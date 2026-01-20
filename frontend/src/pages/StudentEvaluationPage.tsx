import React, { useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { submissionsApi, assignmentsApi, evaluationsApi } from '../lib/api';

const StudentEvaluationPage: React.FC = () => {
    const { submissionId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();

    // 通过路由参数或Query参数确定是自评还是互评
    // 假设 /evaluate/:submissionId?type=self|peer
    const searchParams = new URLSearchParams(location.search);
    const type = searchParams.get('type') as 'self' | 'peer' || 'self';

    const [scores, setScores] = useState<Record<string, number>>({});
    const [feedback, setFeedback] = useState('');

    // 获取提交详情
    const { data: submissionData } = useQuery({
        queryKey: ['submission', submissionId],
        queryFn: () => submissionsApi.getById(Number(submissionId)),
    });
    const submission = submissionData?.data;

    // 获取作业详情 (Rubric)
    const { data: assignmentData } = useQuery({
        queryKey: ['assignment', submission?.assignment_id],
        queryFn: () => assignmentsApi.getById(submission.assignment_id),
        enabled: !!submission,
    });
    const assignment = assignmentData?.data;

    // 提交评价 Mutation
    const submitMutation = useMutation({
        mutationFn: (data: any) => {
            if (type === 'self') {
                return evaluationsApi.createSelf(data);
            } else {
                return evaluationsApi.createPeer(data);
            }
        },
        onSuccess: () => {
            alert('评价已提交');
            navigate(-1);
        },
        onError: (err: any) => {
            alert(`提交失败: ${err.message}`);
        }
    });

    const handleSubmit = () => {
        if (!submission) return;

        // 构造提交数据
        // 注意：SelfEvaluationCreate 和 PeerEvaluationCreate 结构略有不同，但此处简化处理
        const payload: any = {
            submission_id: submission.id,
            dimension_scores_json: scores,
            feedback: feedback
        };

        submitMutation.mutate(payload);
    };

    if (!submission || !assignment) return <div className="p-8 text-center">加载中...</div>;

    return (
        <div className="max-w-4xl mx-auto space-y-6 pb-12">
            <div className="flex items-center gap-4 border-b pb-4">
                <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-800">
                    &larr; 返回
                </button>
                <h1 className="text-2xl font-bold text-gray-900">
                    {type === 'self' ? '自我评价' : '同伴互评'}
                </h1>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* 提交内容展示 */}
                <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
                    <div className="p-4 bg-gray-50 border-b font-semibold text-gray-700">
                        {type === 'self' ? '我的提交' : '同学的作业'}
                    </div>
                    <div className="p-6 space-y-4 max-h-[600px] overflow-y-auto">
                        <div className="bg-gray-50 p-4 rounded-lg text-gray-800 whitespace-pre-wrap">
                            {submission.content_json?.text || '无文本内容'}
                        </div>
                        {submission.attachments_json?.map((att: any, idx: number) => (
                            <a key={idx} href={att.url} target="_blank" rel="noreferrer" className="block text-blue-600 hover:underline">
                                📎 {att.filename}
                            </a>
                        ))}
                    </div>
                </div>

                {/* 评价表单 */}
                <div className="bg-white border rounded-xl overflow-hidden shadow-sm flex flex-col">
                    <div className="p-4 bg-gray-50 border-b font-semibold text-gray-700">
                        评价表
                    </div>
                    <div className="p-6 space-y-6 flex-1 overflow-y-auto">
                        {assignment.rubric_json?.dimensions?.map((dim: any) => (
                            <div key={dim.name} className="space-y-2">
                                <div className="flex justify-between">
                                    <label className="font-medium text-gray-700">{dim.name}</label>
                                    <span className="font-bold text-blue-600">{scores[dim.name] || 0} 分</span>
                                </div>
                                <p className="text-xs text-gray-500">{dim.description}</p>
                                <input
                                    type="range"
                                    min="0"
                                    max="100" // 简化处理，假设满分100
                                    value={scores[dim.name] || 0}
                                    onChange={(e) => setScores(prev => ({ ...prev, [dim.name]: Number(e.target.value) }))}
                                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                                />
                            </div>
                        ))}

                        <div className="space-y-2">
                            <label className="font-medium text-gray-700">评语与建议</label>
                            <textarea
                                rows={4}
                                value={feedback}
                                onChange={(e) => setFeedback(e.target.value)}
                                className="w-full border rounded-lg p-3 focus:ring-2 focus:ring-blue-500 outline-none"
                                placeholder="请客观评价，指出优点和改进建议..."
                            />
                        </div>
                    </div>

                    <div className="p-4 border-t bg-gray-50 text-right">
                        <button
                            onClick={handleSubmit}
                            disabled={submitMutation.isPending}
                            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition font-medium shadow-md"
                        >
                            {submitMutation.isPending ? '提交中...' : '提交评价'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default StudentEvaluationPage;
