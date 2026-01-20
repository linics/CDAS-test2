import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { apiClient } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, Plus, UserPlus } from 'lucide-react';

// Types
interface Member {
    name: string;
    role: string;
}
interface Group {
    id: number;
    assignment_id: number;
    name: string;
    members: Member[];
}

export default function GroupsPage() {
    const [searchParams] = useSearchParams();
    const assignmentId = searchParams.get('assignment_id'); // Optional filter
    const queryClient = useQueryClient();
    const [isCreating, setIsCreating] = useState(false);

    // Queries
    const { data: groups, isLoading } = useQuery<Group[]>({
        queryKey: ['groups', assignmentId],
        queryFn: async () => {
            const url = assignmentId ? `/api/groups?assignment_id=${assignmentId}` : '/api/groups';
            const res = await apiClient.get(url);
            return res.data;
        }
    });

    // Mutations
    const createGroupMutation = useMutation({
        mutationFn: async (data: { name: string, assignment_id: number, members: Member[] }) => {
            const res = await apiClient.post('/api/groups', data);
            return res.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['groups'] });
            setIsCreating(false);
        }
    });

    // Simple create form state
    const [newGroupName, setNewGroupName] = useState('');
    const [newTargetAssignmentId, setNewTargetAssignmentId] = useState(assignmentId || '');

    const handleCreate = (e: React.FormEvent) => {
        e.preventDefault();
        if (!newTargetAssignmentId) return alert("需要任务 ID");

        createGroupMutation.mutate({
            name: newGroupName,
            assignment_id: parseInt(newTargetAssignmentId),
            members: [
                { name: "学生 A", role: "组长" },
                { name: "学生 B", role: "成员" }
            ] // Mock members
        });
    };

    if (isLoading) return <div className="p-8 flex justify-center"><Loader2 className="animate-spin" /></div>;

    return (
        <div className="space-y-6 archive-section">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">学生小组</h1>
                    <p className="text-muted-foreground">管理项目团队和成员资格。</p>
                </div>
                <Button onClick={() => setIsCreating(!isCreating)}>
                    <Plus className="h-4 w-4 mr-2" />
                    新建小组
                </Button>
            </div>

            {isCreating && (
                <Card className="bg-slate-50 border-blue-200">
                    <CardContent className="pt-6">
                        <form onSubmit={handleCreate} className="flex gap-4 items-end">
                            <div className="space-y-2">
                                <label className="text-sm font-medium">小组名称</label>
                                <input
                                    className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                                    value={newGroupName}
                                    onChange={e => setNewGroupName(e.target.value)}
                                    placeholder="例如：Alpha 小组"
                                    required
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium">任务 ID</label>
                                <input
                                    className="flex h-9 w-20 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
                                    value={newTargetAssignmentId}
                                    onChange={e => setNewTargetAssignmentId(e.target.value)}
                                    placeholder="ID"
                                    type="number"
                                    required
                                />
                            </div>
                            <Button type="submit" disabled={createGroupMutation.isPending}>
                                {createGroupMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "创建"}
                            </Button>
                        </form>
                    </CardContent>
                </Card>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {groups?.map((group) => (
                    <Card key={group.id}>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-lg flex justify-between">
                                {group.name}
                                <span className="text-xs font-normal text-muted-foreground bg-slate-100 px-2 py-1 rounded">ID: {group.id}</span>
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-sm text-gray-500 mb-4">任务 ID：{group.assignment_id}</div>
                            <div className="space-y-2">
                                <h4 className="text-xs font-semibold text-gray-900 uppercase tracking-wider">成员</h4>
                                <div className="space-y-1">
                                    {group.members.map((m, i) => (
                                        <div key={i} className="flex justify-between text-sm">
                                            <span>{m.name}</span>
                                            <span className="text-gray-400 text-xs">{m.role}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="mt-4 pt-4 border-t flex gap-2">
                                <Button size="sm" variant="outline" className="w-full">
                                    <UserPlus className="h-4 w-4 mr-2" /> 编辑
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>
            {groups?.length === 0 && (
                <div className="text-center py-12 text-muted-foreground">
                    未找到小组。
                </div>
            )}
        </div>
    );
}
