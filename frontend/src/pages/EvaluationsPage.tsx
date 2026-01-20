import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { assignmentsApi, submissionsApi } from '../lib/api';

const EvaluationsPage: React.FC = () => {
    // 获取所有已发布的作业
    const { data: assignmentsData, isLoading: assignmentsLoading } = useQuery({
        queryKey: ['assignments-published'],
        queryFn: () => assignmentsApi.list(1, 100, true), // published_only = true
    });

    const assignments = assignmentsData?.data.assignments || [];

    if (assignmentsLoading) {
        return <div className="p-8 text-center text-gray-500">加载中...</div>;
    }

    return (
        <div className="space-y-6 archive-section">
            <div>
                <h1 className="text-2xl font-bold archive-title">评价批改</h1>
                <p className="archive-subtitle mt-1">查看学生提交并进行评价。</p>
            </div>

            <div className="grid gap-4">
                {assignments.length === 0 ? (
                    <div className="text-center py-12 archive-card border border-dashed text-gray-400">
                        暂无已发布的作业
                    </div>
                ) : (
                    assignments.map((assignment: any) => (
                        <AssignmentEvalCard key={assignment.id} assignment={assignment} />
                    ))
                )}
            </div>
        </div>
    );
};

// 单个作业评价卡片
const AssignmentEvalCard: React.FC<{ assignment: any }> = ({ assignment }) => {
    // 获取该作业的所有提交
    const { data: submissionsData } = useQuery({
        queryKey: ['submissions-for-eval', assignment.id],
        queryFn: () => submissionsApi.listByAssignment(assignment.id),
    });

    const submissions = submissionsData?.data.submissions || [];
    const pendingCount = submissions.filter((s: any) => s.status === 'submitted').length;
    const gradedCount = submissions.filter((s: any) => s.status === 'graded').length;

    return (
        <div className="archive-card p-6 hover:shadow-md transition">
            <div className="flex justify-between items-start">
                <div className="flex-1">
                    <h3 className="text-lg font-bold archive-title mb-1">{assignment.title}</h3>
                    <p className="text-sm archive-subtitle mb-3">{assignment.topic}</p>
                    <div className="flex gap-4 text-sm">
                        <span className="flex items-center gap-1 text-amber-600">
                            <span className="w-2 h-2 bg-amber-500 rounded-full"></span>
                            待批改: {pendingCount}
                        </span>
                        <span className="flex items-center gap-1 text-green-600">
                            <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                            已批改: {gradedCount}
                        </span>
                        <span className="text-gray-400">
                            共 {submissions.length} 份提交
                        </span>
                    </div>
                </div>
                <Link
                    to={`/assignments/${assignment.id}/submissions`}
                    className="archive-button px-4 py-2 transition text-sm font-medium"
                >
                    查看提交
                </Link>
            </div>
        </div>
    );
};

export default EvaluationsPage;
