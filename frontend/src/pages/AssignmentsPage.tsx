import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { assignmentsApi } from '../lib/api';
import type { Assignment } from '../lib/api';

const AssignmentsPage: React.FC = () => {
    const queryClient = useQueryClient();
    const [filter, setFilter] = useState<'all' | 'published' | 'draft'>('all');

    // 获取作业列表
    const { data, isLoading, error } = useQuery({
        queryKey: ['assignments'],
        queryFn: () => assignmentsApi.list(1, 100), // 获取所有，分页暂简化
    });

    // 删除作业 Mutation
    const deleteMutation = useMutation({
        mutationFn: assignmentsApi.delete,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['assignments'] });
            alert('作业已删除');
        },
        onError: (err: any) => {
            alert(`删除失败: ${err.response?.data?.detail || err.message}`);
        }
    });

    // 发布作业 Mutation
    const publishMutation = useMutation({
        mutationFn: assignmentsApi.publish,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['assignments'] });
            alert('作业已发布');
        },
        onError: (err: any) => {
            alert(`发布失败: ${err.response?.data?.detail || err.message}`);
        }
    });

    const handleDelete = (id: number) => {
        if (window.confirm('确定要删除这个作业吗？此操作无法撤销。')) {
            deleteMutation.mutate(id);
        }
    };

    const handlePublish = (id: number) => {
        if (window.confirm('确定要发布这个作业吗？发布后学生将可见。')) {
            publishMutation.mutate(id);
        }
    };

    // 过滤逻辑
    const filteredAssignments = data?.data.assignments.filter((a: Assignment) => {
        if (filter === 'published') return a.is_published;
        if (filter === 'draft') return !a.is_published;
        return true;
    });

    if (isLoading) {
        return <div className="p-8 text-center text-gray-500">加载中...</div>;
    }

    if (error) {
        return (
            <div className="p-8 text-center">
                <div className="text-red-500 mb-4">
                    加载失败: {(error as any).response?.data?.detail || (error as Error).message}
                </div>
                <div className="text-sm text-gray-500 mb-4">
                    {(error as any).code === 'ERR_NETWORK' ? '网络连接失败，请检查后端服务是否运行' : ''}
                </div>
                <button
                    onClick={() => queryClient.invalidateQueries({ queryKey: ['assignments'] })}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                    重试
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">作业管理</h1>
                    <p className="text-gray-500 mt-1">创建和管理跨学科作业。</p>
                </div>
                <Link
                    to="/assignments/new"
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition shadow-sm font-medium flex items-center gap-2"
                >
                    <span>+</span> 创建新作业
                </Link>
            </div>

            {/* 过滤器 */}
            <div className="flex gap-2 border-b pb-2">
                <button
                    onClick={() => setFilter('all')}
                    className={`px-4 py-2 rounded-md transition ${filter === 'all' ? 'bg-gray-100 font-bold text-blue-600' : 'text-gray-500 hover:bg-gray-50'}`}
                >
                    全部
                </button>
                <button
                    onClick={() => setFilter('published')}
                    className={`px-4 py-2 rounded-md transition ${filter === 'published' ? 'bg-gray-100 font-bold text-green-600' : 'text-gray-500 hover:bg-gray-50'}`}
                >
                    已发布
                </button>
                <button
                    onClick={() => setFilter('draft')}
                    className={`px-4 py-2 rounded-md transition ${filter === 'draft' ? 'bg-gray-100 font-bold text-amber-600' : 'text-gray-500 hover:bg-gray-50'}`}
                >
                    草稿
                </button>
            </div>

            {/* 列表 */}
            <div className="grid gap-4">
                {filteredAssignments?.length === 0 ? (
                    <div className="text-center py-12 bg-white rounded-xl border border-dashed text-gray-400">
                        暂无相关作业
                    </div>
                ) : (
                    filteredAssignments?.map((assignment: Assignment) => (
                        <div
                            key={assignment.id}
                            className="bg-white border rounded-xl p-6 hover:shadow-md transition flex justify-between items-start"
                        >
                            <div>
                                <div className="flex items-center gap-3 mb-2">
                                    <h3 className="text-lg font-bold text-gray-900">
                                        <Link to={`/assignments/${assignment.id}`} className="hover:text-blue-600 hover:underline">
                                            {assignment.title}
                                        </Link>
                                    </h3>
                                    {assignment.is_published ? (
                                        <span className="bg-green-100 text-green-700 text-xs px-2 py-0.5 rounded-full font-medium">已发布</span>
                                    ) : (
                                        <span className="bg-amber-100 text-amber-700 text-xs px-2 py-0.5 rounded-full font-medium">草稿</span>
                                    )}
                                    <span className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full">
                                        {getGradeLabel(assignment.grade)}
                                    </span>
                                    <span className="bg-blue-50 text-blue-600 text-xs px-2 py-0.5 rounded-full">
                                        {getAssignmentTypeLabel(assignment.assignment_type)}
                                    </span>
                                </div>
                                <p className="text-gray-600 mb-4 line-clamp-2">{assignment.description || '暂无描述'}</p>
                                <div className="flex items-center gap-6 text-sm text-gray-500">
                                    <span className="flex items-center gap-1">
                                        <span>📚</span> {assignment.topic}
                                    </span>
                                    <span className="flex items-center gap-1">
                                        <span>🕒</span> {new Date(assignment.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                            </div>

                            <div className="flex flex-col gap-2">
                                <div className="flex gap-2">
                                    <Link
                                        to={`/assignments/${assignment.id}/edit`}
                                        className="px-3 py-1.5 border rounded text-sm text-gray-600 hover:bg-gray-50 hover:text-blue-600 transition"
                                    >
                                        编辑
                                    </Link>
                                    {!assignment.is_published && (
                                        <button
                                            onClick={() => handlePublish(assignment.id)}
                                            className="px-3 py-1.5 bg-green-50 text-green-600 border border-green-200 rounded text-sm hover:bg-green-100 transition"
                                        >
                                            发布
                                        </button>
                                    )}
                                    <button
                                        onClick={() => handleDelete(assignment.id)}
                                        className="px-3 py-1.5 border border-red-200 text-red-600 rounded text-sm hover:bg-red-50 transition"
                                    >
                                        删除
                                    </button>
                                </div>
                                <div className="flex gap-2 mt-2">
                                    <Link
                                        to={`/assignments/${assignment.id}/submissions`}
                                        className="px-3 py-1.5 text-center w-full bg-gray-50 text-gray-700 rounded text-sm hover:bg-gray-100 transition"
                                    >
                                        查看提交
                                    </Link>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

// 辅助函数
const getGradeLabel = (grade: number) => {
    if (grade <= 6) return `小学${grade}年级`;
    return `初中${grade - 6}年级`;
};

const getAssignmentTypeLabel = (type: string) => {
    const map: Record<string, string> = {
        practical: '实践性',
        inquiry: '探究性',
        project: '项目式'
    };
    return map[type] || type;
};

export default AssignmentsPage;
