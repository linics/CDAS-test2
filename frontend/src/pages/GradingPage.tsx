import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { submissionsApi, assignmentsApi, evaluationsApi } from '../lib/api';
import type { TeacherEvaluationCreate } from '../lib/api';

const GradingPage: React.FC = () => {
    const { submissionId } = useParams();
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const [evaluation, setEvaluation] = useState<Partial<TeacherEvaluationCreate>>({
        score_numeric: 3,
        feedback: '',
        dimension_scores_json: {},
    });
    const scoreLabels: Record<number, string> = {
        1: '需改进',
        2: '合格',
        3: '良好',
        4: '优秀',
    };
    const getScoreLabel = (score?: number) => scoreLabels[score ?? 3] || '良好';

    // 获取提交详情
    const { data: submissionData } = useQuery({
        queryKey: ['submission', submissionId],
        queryFn: () => submissionsApi.getById(Number(submissionId)),
    });

    const submission = submissionData?.data;

    // 获取作业详情 (为了获取Rubric)
    const { data: assignmentData } = useQuery({
        queryKey: ['assignment', submission?.assignment_id],
        queryFn: () => assignmentsApi.getById(submission.assignment_id),
        enabled: !!submission,
    });

    const assignment = assignmentData?.data;

    // AI 辅助评分 Mutation
    const aiAssistMutation = useMutation({
        mutationFn: evaluationsApi.aiAssist,
        onSuccess: (data) => {
            const suggestion = data.data.suggestion;
            setEvaluation(prev => ({
                ...prev,
                score_numeric: suggestion.suggested_score,
                feedback: suggestion.feedback,
                dimension_scores_json: suggestion.dimension_scores,
            }));
            alert("已生成 AI 评分建议，请复核。");
        },
        onError: (err: any) => {
            alert(`AI 辅助评分失败: ${err.message}`);
        }
    });

    // 提交评分 Mutation
    const submitEvalMutation = useMutation({
        mutationFn: evaluationsApi.createTeacher,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['submissions'] });
            queryClient.invalidateQueries({ queryKey: ['submission', submissionId] });
            alert("评分已提交");
            navigate(-1);
        },
        onError: (err: any) => {
            alert(`提交失败: ${err.response?.data?.detail || err.message}`);
        }
    });

    const handleSubmit = () => {
        if (!submissionId) return;
        submitEvalMutation.mutate({
            submission_id: Number(submissionId),
            score_numeric: evaluation.score_numeric,
            feedback: evaluation.feedback || '',
            dimension_scores_json: evaluation.dimension_scores_json,
        });
    };

    const handleDimensionScoreChange = (dimName: string, score: number) => {
        setEvaluation(prev => ({
            ...prev,
            dimension_scores_json: {
                ...prev.dimension_scores_json,
                [dimName]: score
            }
        }));
    };

    if (!submission || !assignment) return <div className="p-8 text-center">加载中...</div>;

    return (
        <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-8 h-[calc(100vh-100px)]">

            {/* 左侧：学生提交内容 */}
            <div className="archive-card flex flex-col h-full overflow-hidden">
                <div className="p-4 border-b flex justify-between items-center">
                    <h2 className="font-bold text-lg archive-title">学生提交内容</h2>
                    <div className="text-sm text-gray-500">
                        第 {submission.phase_index + 1} 阶段
                    </div>
                </div>
                <div className="p-6 overflow-y-auto flex-1 space-y-6">

                    {/* 文本内容 */}
                    {submission.content_json && Object.keys(submission.content_json).length > 0 && (
                        <div className="space-y-2">
                            <h3 className="font-medium text-gray-700">文本回答</h3>
                            <div className="archive-section p-4 text-gray-800 whitespace-pre-wrap">
                                {JSON.stringify(submission.content_json, null, 2)}
                            </div>
                        </div>
                    )}

                    {/* 附件 */}
                    {submission.attachments_json && submission.attachments_json.length > 0 && (
                        <div className="space-y-2">
                            <h3 className="font-medium text-gray-700">附件</h3>
                            <div className="grid gap-2">
                                {submission.attachments_json.map((att: any, idx: number) => (
                                    <a
                                        key={idx}
                                        href={att.url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="archive-section flex items-center gap-3 p-3 hover:bg-white/70 transition"
                                    >
                                        <span className="text-2xl">📄</span>
                                        <div className="flex-1 overflow-hidden">
                                            <div className="font-medium truncate">{att.filename}</div>
                                            <div className="text-xs text-gray-500">{att.type}</div>
                                        </div>
                                    </a>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 检查点 */}
                    {submission.checkpoints_json && (
                        <div className="space-y-2">
                            <h3 className="font-medium text-gray-700">检查点完成情况</h3>
                            <div className="space-y-1">
                                {Object.entries(submission.checkpoints_json).map(([key, val]) => (
                                    <div key={key} className="flex items-center gap-2">
                                        <span className={val ? "text-green-600" : "text-gray-400"}>
                                            {val ? "✅" : "⭕"}
                                        </span>
                                        <span className="text-sm">{key}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* 右侧：评分面板 */}
            <div className="archive-card flex flex-col h-full overflow-hidden">
                <div className="p-4 border-b flex justify-between items-center">
                    <h2 className="font-bold text-lg archive-title">评分与反馈</h2>
                    <button
                        onClick={() => aiAssistMutation.mutate(submission.id)}
                        disabled={aiAssistMutation.isPending}
                        className="archive-badge bg-amber-50 text-amber-700 px-3 py-1 rounded-full hover:bg-amber-100 transition flex items-center gap-1"
                    >
                        <span>✨</span> {aiAssistMutation.isPending ? '生成中...' : 'AI 辅助评分'}
                    </button>
                </div>

                <div className="p-6 overflow-y-auto flex-1 space-y-6">

                    {/* 维度评分 (Rubric) */}
                    <div className="space-y-4">
                        <h3 className="font-medium text-gray-900 border-b pb-2 archive-title">维度评分</h3>
                        {assignment.rubric_json?.dimensions ? (
                            assignment.rubric_json.dimensions.map((dim: any) => (
                                <div key={dim.name} className="space-y-1">
                                    <div className="flex justify-between">
                                        <label className="text-sm font-medium text-gray-700">{dim.name} (权重 {dim.weight}%)</label>
                                        <span className="text-sm font-bold text-blue-600">
                                            {evaluation.dimension_scores_json?.[dim.name] ?? 3} 分（{getScoreLabel(evaluation.dimension_scores_json?.[dim.name])}）
                                        </span>
                                    </div>
                                    <input
                                        type="range"
                                        min="1"
                                        max="4"
                                        step="1"
                                        value={evaluation.dimension_scores_json?.[dim.name] ?? 3}
                                        onChange={(e) => handleDimensionScoreChange(dim.name, Number(e.target.value))}
                                        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                                    />
                                    <p className="text-xs text-gray-500">{dim.description}</p>
                                </div>
                            ))
                        ) : (
                            <div className="text-gray-400 text-sm">未设置详细评价维度</div>
                        )}
                    </div>

                    {/* 总评 */}
                    <div className="bg-gray-50 p-4 rounded-xl space-y-2">
                        <div className="flex justify-between items-center">
                            <label className="block text-sm font-medium text-gray-700">总评价</label>
                            <span className="text-sm font-bold text-blue-600">
                                {evaluation.score_numeric ?? 3} 分（{getScoreLabel(evaluation.score_numeric)}）
                            </span>
                        </div>
                        <input
                            type="range"
                            min="1"
                            max="4"
                            step="1"
                            value={evaluation.score_numeric ?? 3}
                            onChange={(e) => setEvaluation(prev => ({ ...prev, score_numeric: Number(e.target.value) }))}
                            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                        />
                        <div className="text-xs text-gray-500">1=需改进，2=合格，3=良好，4=优秀</div>
                    </div>

                    {/* 评语 */}
                    <div className="space-y-2">
                        <h3 className="font-medium text-gray-900">教师评语</h3>
                        <textarea
                            rows={6}
                            value={evaluation.feedback}
                            onChange={(e) => setEvaluation(prev => ({ ...prev, feedback: e.target.value }))}
                            className="w-full border rounded-lg p-3 focus:ring-2 focus:ring-blue-500 outline-none"
                            placeholder="请输入评语和建议..."
                        />
                    </div>

                </div>

                <div className="p-4 border-t bg-gray-50 flex justify-end gap-3">
                    <button
                        onClick={() => navigate(-1)}
                        className="px-4 py-2 text-gray-600 hover:text-gray-800"
                    >
                        取消
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={submitEvalMutation.isPending}
                        className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition shadow-sm font-medium disabled:opacity-70"
                    >
                        {submitEvalMutation.isPending ? '提交中...' : '提交评分'}
                    </button>
                </div>
            </div>

        </div>
    );
};

export default GradingPage;
