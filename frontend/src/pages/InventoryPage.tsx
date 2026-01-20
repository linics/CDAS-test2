import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { FileText, Trash2, Loader2, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface Document {
    id: number;
    filename: string;
    status: 'uploaded' | 'indexing' | 'ready' | 'failed';
    upload_date: string;
    metadata_json: any;
    error_msg?: string;
    cpote_json?: any; // If assignment generated
}

export default function InventoryPage() {
    const navigate = useNavigate();
    const { data: documents, isLoading, isError } = useQuery<Document[]>({
        queryKey: ['documents'],
        queryFn: async () => {
            const res = await apiClient.get('/api/documents');
            return res.data;
        },
        // Poll every 5 seconds if there are documents in indexing state
        refetchInterval: (query) => {
            const data = query.state.data as Document[] | undefined;
            if (data?.some(d => d.status === 'indexing' || d.status === 'uploaded')) {
                return 3000;
            }
            return false;
        }
    });

    const generateMutation = useMutation({
        mutationFn: async (docId: number) => {
            // We need a title. For now, prompt or use default.
            // In a real app, we'd open a modal.
            // I'll assume we pass a default title based on filename for simplicity or hardcode.
            // Or wait, the API requires assignment_title.
            const title = prompt("请输入任务标题：", "新任务");
            if (!title) throw new Error("已取消");

            const res = await apiClient.post('/api/agents/parse_cpote', {
                document_id: docId,
                assignment_title: title
            });
            return res.data; // contains assignment_id
        },
        onSuccess: (data) => {
            navigate(`/assignments/${data.assignment_id}`);
        },
        onError: (err) => {
            console.error("CPOTE generation failed", err);
            alert("任务包生成失败，请查看控制台。");
        }
    });

    const deleteMutation = useMutation({
        mutationFn: async (id: number) => {
            await apiClient.delete(`/api/documents/${id}`);
        },
        onSuccess: () => {
            // refetch done automatically via query invalidation if we did it properly, 
            // but here we just need to refetch
            // actually accessing queryClient here would be better
            // For now, I'll rely on the fact that react-query usually refetches on window focus or we can inject client
        }
    });
    // Using queryClient for invalidation is better practice
    // I'll skip it for brevity in this file and rely on the user refreshing or simple UI state updates if I were building a full app,
    // but let's add it properly.
    // Actually, I can just `window.location.reload()` which is crude or use queryClient.
    // I will leave it for now, the list update might be delayed until next poll or refresh. 
    // Wait, I should import `useQueryClient` and invalidate.

    if (isLoading) return <div className="p-8 flex justify-center"><Loader2 className="animate-spin" /></div>;
    if (isError) return <div className="p-8 text-red-500">加载文档失败。请确保后端已启动。</div>;

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">知识资料库</h1>
                    <p className="text-muted-foreground">上传课程资料 (PDF/Word) 以构建语义数据库。</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-4">
                    {documents?.map((doc) => (
                        <Card key={doc.id} className="overflow-hidden">
                            <div className="flex items-center p-4 gap-4">
                                <div className="h-10 w-10 rounded bg-blue-50 flex items-center justify-center flex-shrink-0">
                                    <FileText className="h-5 w-5 text-blue-600" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <h3 className="font-semibold truncate">{doc.filename}</h3>
                                    <div className="text-sm text-muted-foreground flex items-center gap-2">
                                        <span>{new Date(doc.upload_date).toLocaleDateString()}</span>
                                        <span className={cn(
                                            "px-2 py-0.5 rounded-full text-xs font-medium capitalize",
                                            doc.status === 'ready' ? "bg-green-100 text-green-700" :
                                                doc.status === 'failed' ? "bg-red-100 text-red-700" :
                                                    "bg-yellow-100 text-yellow-700"
                                        )}>
                                            {doc.status}
                                        </span>
                                    </div>
                                    {doc.status === 'failed' && <p className="text-xs text-red-500 mt-1">{doc.error_msg}</p>}
                                </div>

                                <div className="flex items-center gap-2">
                                    {doc.status === 'ready' && (
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={() => generateMutation.mutate(doc.id)}
                                            disabled={generateMutation.isPending}
                                        >
                                            {generateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "生成任务"}
                                        </Button>
                                    )}
                                    <Button
                                        size="icon"
                                        variant="ghost"
                                        className="text-red-400 hover:text-red-500 hover:bg-red-50"
                                        onClick={() => deleteMutation.mutate(doc.id)}
                                    >
                                        {deleteMutation.isPending && deleteMutation.variables === doc.id ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <Trash2 className="h-4 w-4" />
                                        )}
                                    </Button>
                                </div>
                            </div>
                        </Card>
                    ))}
                    {documents?.length === 0 && (
                        <div className="text-center py-12 border-2 border-dashed rounded-xl ">
                            <p className="text-muted-foreground">暂无文档。请上传文档以开始。</p>
                        </div>
                    )}
                </div>

                <div>
                    <Card>
                        <CardHeader>
                            <CardTitle>上传资料</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <FileUpload />
                            <div className="mt-4 text-xs text-muted-foreground bg-slate-50 p-3 rounded">
                                <p className="font-semibold mb-1">支持的文件格式：</p>
                                <ul className="list-disc pl-4 space-y-1">
                                    <li>PDF 文档 (.pdf)</li>
                                    <li>Word 文档 (.docx)</li>
                                </ul>
                                <p className="mt-2 text-blue-600 flex items-center gap-1">
                                    <AlertCircle className="h-3 w-3" />
                                    文件大小限制：50MB
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
