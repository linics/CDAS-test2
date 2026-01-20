import { useQuery } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import { assignmentsApi } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Loader2, Calendar, Users, CheckCircle2 } from 'lucide-react';

interface Milestone {
    index: number;
    name: string;
    description: string;
    due_at?: string;
    submission_requirements?: string;
}

interface Group {
    id: number;
    name: string;
    members: { name: string; role: string }[];
}

interface Assignment {
    assignment_id: number;
    title: string;
    cpote: any;
    milestones: Milestone[];
    groups: Group[];
}

export default function AssignmentPage() {
    const { id } = useParams<{ id: string }>();

    const { data: assignment, isLoading, isError } = useQuery<Assignment>({
        queryKey: ['assignment', id],
        queryFn: async () => {
            const res = await assignmentsApi.getById(Number(id));
            return res.data;
        },
        enabled: !!id
    });

    if (isLoading) return <div className="p-8 flex justify-center"><Loader2 className="animate-spin" /></div>;
    if (isError || !assignment) return <div className="p-8 text-red-500">加载作业失败。</div>;

    return (
        <div className="space-y-8 archive-section">
            <div className="flex justify-between items-start">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight archive-title">{assignment.title}</h1>
                    <p className="text-muted-foreground mt-2 max-w-2xl">
                        {assignment.cpote?.problem_statement || "未找到问题陈述。"}
                    </p>
                </div>
                <div className="flex gap-2">
                    {/* Action buttons could go here */}
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <CheckCircle2 className="h-5 w-5 text-blue-600" />
                                项目路线图（里程碑）
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="relative border-l border-gray-200 ml-4 space-y-8 pb-4">
                                {assignment.milestones.map((milestone) => (
                                    <div key={milestone.index} className="ml-6 relative">
                                        <span className="absolute -left-[33px] flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 ring-4 ring-white text-blue-600 font-bold text-sm">
                                            {milestone.index}
                                        </span>
                                        <h3 className="flex items-center text-lg font-semibold text-gray-900">
                                            {milestone.name}
                                            {milestone.due_at && (
                                                <span className="ml-3 text-xs font-medium bg-gray-100 text-gray-800 px-2 py-0.5 rounded flex items-center gap-1">
                                                    <Calendar className="h-3 w-3" />
                                                    {new Date(milestone.due_at).toLocaleDateString()}
                                                </span>
                                            )}
                                        </h3>
                                        <p className="mb-2 text-base font-normal text-gray-500 mt-1">
                                            {milestone.description}
                                        </p>
                                        {milestone.submission_requirements && (
                                            <div className="text-sm bg-yellow-50 text-yellow-800 p-2 rounded mt-2 border border-yellow-100">
                                                <strong>要求：</strong> {milestone.submission_requirements}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Users className="h-5 w-5 text-indigo-600" />
                                项目小组
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {assignment.groups.length > 0 ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {assignment.groups.map(group => (
                                        <div key={group.id} className="p-4 border rounded-lg hover:bg-slate-50 transition">
                                            <div className="flex justify-between items-center mb-2">
                                                <h4 className="font-semibold">{group.name}</h4>
                                                <Link to={`/submissions?group_id=${group.id}`} className="text-xs text-blue-600 hover:underline">
                                                    查看进度 &rarr;
                                                </Link>
                                            </div>
                                            <div className="flex flex-wrap gap-1">
                                                {group.members.map(m => (
                                                    <span key={m.name} className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600">
                                                        {m.name} <span className="text-gray-400 ml-1">({m.role})</span>
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-6 text-muted-foreground">
                                    暂无已组建的小组。
                                    <Link to="/groups" className="ml-2 text-blue-600 hover:underline">管理小组</Link>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>

                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>学习目标</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <ul className="list-disc pl-4 space-y-2 text-sm text-gray-600">
                                {assignment.cpote?.objectives?.map((obj: string, i: number) => (
                                    <li key={i}>{obj}</li>
                                )) || <li>未定义学习目标。</li>}
                            </ul>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
