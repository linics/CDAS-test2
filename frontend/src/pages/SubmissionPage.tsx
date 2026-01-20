import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { apiClient } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, Send, CheckCircle, FileText } from 'lucide-react';

export default function SubmissionPage() {
    const [searchParams] = useSearchParams();
    const groupId = searchParams.get('group_id');

    // State for new submission
    const [milestoneIndex, setMilestoneIndex] = useState('1');
    const [submissionText, setSubmissionText] = useState('');
    const [targetAssignmentId, setTargetAssignmentId] = useState('');
    const [targetGroupId, setTargetGroupId] = useState(groupId || '');

    const submitMutation = useMutation({
        mutationFn: async (data: any) => {
            const res = await apiClient.post('/api/submissions', data);
            return res.data;
        },
        onSuccess: (data) => {
            alert(`提交已保存！ID：${data.submission_id}`);
        },
        onError: (err) => {
            console.error(err);
            alert("提交失败");
        }
    });

    const evaluateMutation = useMutation({
        mutationFn: async (data: { group_id: number, milestone_index: number, content: any }) => {
            const res = await apiClient.post('/api/agents/evaluate_submission', data);
            return res.data;
        },
        onSuccess: (data) => {
            console.log(data);
            alert("评估完成！详情请查看控制台。");
        },
        onError: (err) => {
            console.error(err);
            alert("评估失败");
        }
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const payload = {
            assignment_id: parseInt(targetAssignmentId),
            group_id: parseInt(targetGroupId),
            milestone_index: parseInt(milestoneIndex),
            content: {
                text: submissionText,
                attachments: []
            }
        };
        submitMutation.mutate(payload);
    };

    return (
        <div className="space-y-6 archive-section">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">提交与评估</h1>
                <p className="text-muted-foreground">提交里程碑进度并接收 AI 反馈。</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <Card>
                    <CardHeader>
                        <CardTitle>新建提交</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium">任务 ID</label>
                                    <input
                                        className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm text-black"
                                        value={targetAssignmentId}
                                        onChange={e => setTargetAssignmentId(e.target.value)}
                                        required
                                        type="number"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-sm font-medium">小组 ID</label>
                                    <input
                                        className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm text-black"
                                        value={targetGroupId}
                                        onChange={e => setTargetGroupId(e.target.value)}
                                        required
                                        type="number"
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium">里程碑索引</label>
                                <input
                                    className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm text-black"
                                    value={milestoneIndex}
                                    onChange={e => setMilestoneIndex(e.target.value)}
                                    type="number"
                                    min="1"
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium">内容</label>
                                <textarea
                                    className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-black"
                                    value={submissionText}
                                    onChange={e => setSubmissionText(e.target.value)}
                                    placeholder="描述你的进度......"
                                    required
                                />
                            </div>

                            <div className="flex gap-2">
                                <Button type="submit" disabled={submitMutation.isPending}>
                                    {submitMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Send className="h-4 w-4 mr-2" />}
                                    提交作业
                                </Button>
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={() => evaluateMutation.mutate({
                                        group_id: parseInt(targetGroupId),
                                        milestone_index: parseInt(milestoneIndex),
                                        content: { text: submissionText, attachments: [] }
                                    })}
                                    disabled={evaluateMutation.isPending}
                                >
                                    {evaluateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <CheckCircle className="h-4 w-4 mr-2" />}
                                    触发 AI 评估
                                </Button>
                            </div>
                        </form>
                    </CardContent>
                </Card>

                <div className="space-y-4">
                    <Card className="h-full bg-slate-50 border-dashed flex items-center justify-center">
                        <div className="text-center text-muted-foreground p-6">
                            <FileText className="h-12 w-12 mx-auto mb-4 opacity-20" />
                            <p>选择一个提交以查看评估结果。</p>
                            <p className="text-xs">（列表视图在此版本中尚未实现）</p>
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    );
}
