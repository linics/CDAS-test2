import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { submissionsApi } from '../lib/api';

const StudentSubmissionPage: React.FC = () => {
    const { id } = useParams(); // submission id
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const [content, setContent] = useState<string>('');
    const [attachments, setAttachments] = useState<any[]>([]);
    const evidenceLabels: Record<string, string> = {
        text: '文本',
        document: '文档',
        image: '图片',
        video: '视频',
        link: '链接',
        confirm: '确认',
    };

    // 获取提交详情
    const { data: submissionData, isLoading, isError, error } = useQuery({
        queryKey: ['my-submission', id],
        queryFn: () => submissionsApi.getById(Number(id)),
    });

    const submission = submissionData?.data;
    const assignment = submission?.assignment;

    useEffect(() => {
        if (submission) {
            // 初始化内容 (假设内容存在 content_json.text 中)
            if (submission.content_json?.text) {
                setContent(submission.content_json.text);
            }
            if (submission.attachments_json) {
                setAttachments(submission.attachments_json);
            }
        }
    }, [submission]);

    // 提交作业 Mutation
    const submitMutation = useMutation({
        mutationFn: submissionsApi.submit,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['my-submission', id] });
            alert('作业已提交！');
            navigate('/my-assignments');
        },
        onError: (err: any) => {
            alert(`提交失败: ${err.message}`);
        }
    });

    // 保存草稿 Mutation
    const saveDraftMutation = useMutation({
        mutationFn: (data: any) => submissionsApi.update(Number(id), data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['my-submission', id] });
            alert('草稿已保存');
        },
        onError: (err: any) => {
            alert(`保存失败: ${err.message}`);
        }
    });

    const handleSave = (isSubmit: boolean = false) => {
        const payload = {
            content_json: { text: content },
            attachments_json: attachments,
            // checkPoints handled separately if needed, simplified here
        };

        if (isSubmit) {
            if (window.confirm('确定要提交吗？提交后将无法修改当前阶段内容。')) {
                // Submit API just triggers the status change and validation
                // So we usually save first then submit, or submit takes payload.
                // Assuming submit API takes payload or we update then submit.
                // Let's update first then submit.
                saveDraftMutation.mutateAsync(payload).then(() => {
                    submitMutation.mutate(Number(id));
                });
            }
        } else {
            saveDraftMutation.mutate(payload);
        }
    };

    if (isLoading) return <div className="p-8 text-center">加载中...</div>;
    if (isError) {
        const message = (error as any)?.response?.data?.detail || (error as Error).message || '请稍后再试';
        return <div className="p-8 text-center text-red-500">加载失败: {message}</div>;
    }
    if (!submission) return <div className="p-8 text-center text-gray-500">未找到提交记录</div>;

    const currentPhase = assignment?.phases_json?.[submission.phase_index];
    const isReadOnly = submission.status !== 'draft' && submission.status !== 'returned';

    return (
        <div className="max-w-4xl mx-auto space-y-8 pb-12">

            {/* 头部信息 */}
            <div className="bg-white border rounded-xl p-6 shadow-sm space-y-4">
                <div className="flex justify-between items-start">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">{assignment?.title}</h1>
                        <p className="text-gray-500 mt-1">{assignment?.topic}</p>
                    </div>
                    <span className="bg-blue-100 text-blue-800 text-xs px-3 py-1 rounded-full font-bold">
                        第 {submission.phase_index + 1} 阶段: {currentPhase?.name || '进行中'}
                    </span>
                </div>
                <div className="p-4 bg-blue-50 rounded-lg text-blue-900 text-sm">
                    <strong>阶段任务说明：</strong>
                    <p className="mt-1">{currentPhase?.description || assignment?.description}</p>
                    {Array.isArray(currentPhase?.steps) && currentPhase.steps.length > 0 ? (
                        <div className="mt-4 space-y-3">
                            <div className="font-semibold text-blue-900">阶段任务清单</div>
                            {currentPhase.steps.map((step: any, idx: number) => {
                                const stepTitle =
                                    step?.content || step?.description || step?.name || `步骤 ${idx + 1}`;
                                const showDescription =
                                    step?.description && step?.description !== stepTitle;
                                const checkpoints = Array.isArray(step?.checkpoints) ? step.checkpoints : [];
                                return (
                                    <div key={idx} className="bg-white/70 border border-blue-100 rounded-lg p-3 space-y-2">
                                        <div className="font-medium text-blue-900">
                                            {idx + 1}. {stepTitle}
                                        </div>
                                        {showDescription && (
                                            <p className="text-sm text-blue-800">{step.description}</p>
                                        )}
                                        {checkpoints.length > 0 && (
                                            <ul className="text-sm text-blue-800 space-y-1">
                                                {checkpoints.map((cp: any, cpIdx: number) => {
                                                    const label = cp?.evidence_type ? `(${evidenceLabels[cp.evidence_type] || cp.evidence_type})` : '';
                                                    return (
                                                        <li key={cpIdx} className="flex gap-2">
                                                            <span>•</span>
                                                            <span>{cp?.content || ''} {label}</span>
                                                        </li>
                                                    );
                                                })}
                                            </ul>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <div className="mt-3 text-sm text-blue-800">暂无阶段任务清单</div>
                    )}
                </div>
            </div>

            {/* 提交区域 */}
            <div className="bg-white border rounded-xl shadow-sm overflow-hidden">
                <div className="p-4 bg-gray-50 border-b font-semibold text-gray-700">
                    我的提交内容
                </div>

                <div className="p-6 space-y-6">
                    <div className="space-y-2">
                        <label className="block text-sm font-medium text-gray-700">文本回答 / 实验记录</label>
                        <textarea
                            rows={10}
                            disabled={isReadOnly}
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            className="w-full border rounded-lg p-3 focus:ring-2 focus:ring-blue-500 outline-none disabled:bg-gray-100 disabled:text-gray-500"
                            placeholder="在这里输入你的思考、观察记录或实验结果..."
                        />
                    </div>

                    {/* 简单的附件占位符 - 实际项目应集成 FileUpload 组件 */}
                    <div className="space-y-2">
                        <label className="block text-sm font-medium text-gray-700">附件上传 (暂仅演示)</label>
                        <div className="border-2 border-dashed rounded-lg p-6 text-center text-gray-500 hover:bg-gray-50 transition cursor-pointer">
                            点击上传图片、PDF或实验数据
                        </div>
                    </div>
                </div>

                {!isReadOnly && (
                    <div className="p-4 border-t bg-gray-50 flex justify-end gap-3">
                        <button
                            onClick={() => handleSave(false)}
                            disabled={saveDraftMutation.isPending}
                            className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition"
                        >
                            保存草稿
                        </button>
                        <button
                            onClick={() => handleSave(true)}
                            disabled={submitMutation.isPending}
                            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium shadow-md"
                        >
                            提交作业
                        </button>
                    </div>
                )}
            </div>

            {/* 教师反馈区 */}
            {submission.status === 'graded' && (
                <div className="bg-white border rounded-xl shadow-sm overflow-hidden border-green-200">
                    <div className="p-4 bg-green-50 border-b border-green-200 font-semibold text-green-900 flex justify-between">
                        <span>教师及AI评价反馈</span>
                        <span>{submission.score_level} ({submission.score_numeric}分)</span>
                    </div>
                    <div className="p-6 space-y-4">
                        {submission.evaluation?.radar_json && (
                            <div className="p-4 bg-white border rounded-lg">
                                <h4 className="font-bold text-sm text-gray-700 mb-2">能力雷达图</h4>
                                {/* 此处集成 Recharts 雷达图 */}
                                <div className="h-40 bg-gray-100 flex items-center justify-center text-gray-400 text-xs">
                                    [雷达图组件占位]
                                </div>
                            </div>
                        )}
                        <div>
                            <h4 className="font-bold text-sm text-gray-700 mb-2">详细评语</h4>
                            <p className="text-gray-600 leading-relaxed bg-gray-50 p-4 rounded-lg">
                                {submission.feedback || '暂无详细评语'}
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default StudentSubmissionPage;
