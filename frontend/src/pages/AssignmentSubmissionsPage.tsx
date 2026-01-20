import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { assignmentsApi, submissionsApi } from '../lib/api';

const AssignmentSubmissionsPage: React.FC = () => {
    const { assignmentId } = useParams();
    const [phaseIndex, setPhaseIndex] = useState<number | undefined>(undefined);

    // 获取作业详情
    const { data: assignmentData } = useQuery({
        queryKey: ['assignment', assignmentId],
        queryFn: () => assignmentsApi.getById(Number(assignmentId)),
    });

    // 获取提交列表
    const { data: submissionsData, isLoading } = useQuery({
        queryKey: ['submissions', assignmentId, phaseIndex],
        queryFn: () => submissionsApi.listByAssignment(Number(assignmentId), phaseIndex),
        enabled: !!assignmentId,
    });

    const assignment = assignmentData?.data;
    const submissions = submissionsData?.data.submissions || [];

    if (isLoading) return <div className="p-8 text-center">加载中...</div>;

    return (
        <div className="space-y-6 archive-section">
            <div className="flex items-center gap-4 border-b pb-4">
                <Link to="/assignments" className="text-gray-500 hover:text-gray-800">
                    &larr; 返回列表
                </Link>
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">{assignment?.title} - 提交管理</h1>
                    <p className="text-gray-500 text-sm">查看学生提交并进行评分。</p>
                </div>
            </div>

            {/* 阶段筛选 */}
            {assignment?.phases_json && assignment.phases_json.length > 0 && (
                <div className="flex gap-2 overflow-x-auto pb-2">
                    <button
                        onClick={() => setPhaseIndex(undefined)}
                        className={`px-4 py-2 rounded-lg border whitespace-nowrap transition ${phaseIndex === undefined
                                ? 'bg-blue-600 text-white border-blue-600'
                                : 'bg-white text-gray-700 hover:bg-gray-50'
                            }`}
                    >
                        全部阶段
                    </button>
                    {assignment.phases_json.map((phase: any, index: number) => (
                        <button
                            key={index}
                            onClick={() => setPhaseIndex(index)}
                            className={`px-4 py-2 rounded-lg border whitespace-nowrap transition ${phaseIndex === index
                                    ? 'bg-blue-600 text-white border-blue-600'
                                    : 'bg-white text-gray-700 hover:bg-gray-50'
                                }`}
                        >
                            阶段 {index + 1}: {phase.name}
                        </button>
                    ))}
                </div>
            )}

            {/* 提交列表 */}
            <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">学生/小组</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">阶段</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">提交时间</th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {submissions.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                                    暂无提交记录
                                </td>
                            </tr>
                        ) : (
                            submissions.map((sub: any) => (
                                <tr key={sub.id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="text-sm font-medium text-gray-900">
                                            {sub.student_id} {/* TODO: 显示学生姓名 */}
                                        </div>
                                        <div className="text-sm text-gray-500">
                                            {sub.group_id ? `小组ID: ${sub.group_id}` : '个人作业'}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        第 {sub.phase_index + 1} 阶段
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        {getStatusBadge(sub.status)}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {sub.submitted_at ? new Date(sub.submitted_at).toLocaleString() : '-'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                        <Link
                                            to={`/grading/${sub.id}`}
                                            className="text-blue-600 hover:text-blue-900 bg-blue-50 px-3 py-1.5 rounded"
                                        >
                                            评分
                                        </Link>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
        draft: 'bg-gray-100 text-gray-800',
        submitted: 'bg-blue-100 text-blue-800',
        graded: 'bg-green-100 text-green-800',
    };
    const labels: Record<string, string> = {
        draft: '草稿',
        submitted: '已提交',
        graded: '已评分',
    };
    return (
        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${styles[status] || styles.draft}`}>
            {labels[status] || status}
        </span>
    );
};

export default AssignmentSubmissionsPage;
