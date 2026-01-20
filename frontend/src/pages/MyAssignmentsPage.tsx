import React, { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { assignmentsApi, submissionsApi, type Assignment } from '../lib/api';

const statusLabelMap: Record<string, string> = {
    draft: '进行中',
    submitted: '已提交',
    returned: '待修改',
    graded: '已评分',
};

const typeLabelMap: Record<string, string> = {
    practical: '实践性作业',
    inquiry: '探究性作业',
    project: '项目式作业',
};

const MyAssignmentsPage: React.FC = () => {
    const [filter, setFilter] = useState<'active' | 'completed'>('active');
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const { data: assignmentsData, isLoading: assignmentsLoading, error: assignmentsError } = useQuery({
        queryKey: ['my-assignments'],
        queryFn: () => assignmentsApi.list(1, 100, true),
    });

    const { data: submissionsData, isLoading: submissionsLoading, error: submissionsError } = useQuery({
        queryKey: ['my-submissions'],
        queryFn: () => submissionsApi.listMy(),
    });

    const submissions = submissionsData?.data.submissions || [];
    const assignments: Assignment[] = assignmentsData?.data.assignments || [];

    const submissionByAssignmentId = useMemo(() => {
        const map = new Map<number, any>();
        for (const submission of submissions) {
            if (!map.has(submission.assignment_id)) {
                map.set(submission.assignment_id, submission);
            }
        }
        return map;
    }, [submissions]);

    const createSubmission = useMutation({
        mutationFn: (assignmentId: number) => submissionsApi.create({ assignment_id: assignmentId, phase_index: 0 }),
        onSuccess: (res) => {
            queryClient.invalidateQueries({ queryKey: ['my-submissions'] });
            navigate(`/my-details/${res.data.id}`);
        },
        onError: (err: any) => {
            const message = err.response?.data?.detail || err.message || '创建失败';
            alert(`开始作业失败: ${message}`);
        },
    });

    const filteredAssignments = assignments.filter((assignment) => {
        const submission = submissionByAssignmentId.get(assignment.id);
        const isCompleted = submission?.status === 'graded';
        return filter === 'completed' ? isCompleted : !isCompleted;
    });

    if (assignmentsLoading || submissionsLoading) {
        return <div className="p-8 text-center text-gray-500">加载中...</div>;
    }
    if (assignmentsError || submissionsError) {
        return <div className="p-8 text-center text-red-500">加载失败</div>;
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">我的作业</h1>
                    <p className="text-gray-500 mt-1">查看已发布给你的跨学科作业</p>
                </div>
            </div>

            <div className="flex gap-2 border-b pb-2">
                <button
                    onClick={() => setFilter('active')}
                    className={`px-4 py-2 rounded-md transition ${filter === 'active' ? 'bg-blue-50 font-bold text-blue-600' : 'text-gray-500 hover:bg-gray-50'}`}
                >
                    进行中
                </button>
                <button
                    onClick={() => setFilter('completed')}
                    className={`px-4 py-2 rounded-md transition ${filter === 'completed' ? 'bg-green-50 font-bold text-green-600' : 'text-gray-500 hover:bg-gray-50'}`}
                >
                    已完成
                </button>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {filteredAssignments.length === 0 ? (
                    <div className="col-span-full text-center py-12 bg-white rounded-xl border border-dashed text-gray-400">
                        暂无{filter === 'active' ? '进行中' : '已完成'}的作业
                    </div>
                ) : (
                    filteredAssignments.map((assignment) => {
                        const submission = submissionByAssignmentId.get(assignment.id);
                        const statusLabel = submission ? (statusLabelMap[submission.status] || '进行中') : '未开始';
                        const actionLabel = submission
                            ? (submission.status === 'graded' ? '查看反馈' : '继续作业')
                            : '开始作业';
                        const typeLabel = typeLabelMap[assignment.assignment_type] || '作业';

                        return (
                            <div
                                key={assignment.id}
                                className="bg-white border rounded-xl p-5 hover:shadow-lg transition flex flex-col h-full group"
                            >
                                <div className="mb-4">
                                    <div className="flex justify-between items-start mb-2">
                                        <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
                                            {typeLabel}
                                        </span>
                                        <span
                                            className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                                                submission?.status === 'graded'
                                                    ? 'bg-green-100 text-green-700'
                                                    : submission
                                                        ? 'bg-amber-100 text-amber-700'
                                                        : 'bg-gray-100 text-gray-500'
                                            }`}
                                        >
                                            {statusLabel}
                                        </span>
                                    </div>
                                    <h3 className="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition mb-1 line-clamp-1">
                                        {assignment.title}
                                    </h3>
                                    <p className="text-sm text-gray-500 line-clamp-2 h-10">
                                        {assignment.description || '暂无描述'}
                                    </p>
                                </div>

                                <div className="mt-auto space-y-3">
                                    {submission && (
                                        <div className="flex items-center justify-between text-xs text-gray-500 border-t pt-3">
                                            <div className="flex items-center gap-1">
                                                <span>📍</span> 第{submission.phase_index + 1}阶段
                                            </div>
                                            {submission.score_numeric && (
                                                <div className="font-bold text-green-600">
                                                    {submission.score_numeric}分({submission.score_level})
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {submission ? (
                                        <Link
                                            to={`/my-details/${submission.id}`}
                                            className="block w-full py-2 text-center bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition text-sm font-medium"
                                        >
                                            {actionLabel}
                                        </Link>
                                    ) : (
                                        <button
                                            type="button"
                                            onClick={() => createSubmission.mutate(assignment.id)}
                                            disabled={createSubmission.isPending}
                                            className="block w-full py-2 text-center bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition text-sm font-medium disabled:opacity-60"
                                        >
                                            {createSubmission.isPending ? '创建中...' : actionLabel}
                                        </button>
                                    )}
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
};

export default MyAssignmentsPage;
