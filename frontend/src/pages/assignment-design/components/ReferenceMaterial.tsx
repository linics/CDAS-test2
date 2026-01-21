import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../../lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../../components/ui/card";
import { cn } from "../../../lib/utils";

export function ReferenceMaterial({
    selectedDocId,
    onSelect
}: {
    selectedDocId: number | null,
    onSelect: (id: number | null) => void
}) {
    const { data: documents, isLoading } = useQuery<any[]>({
        queryKey: ['documents'],
        queryFn: async () => {
            const res = await apiClient.get('/api/documents');
            return res.data;
        }
    });

    const readyDocs = documents?.filter(d => d.status === 'ready') || [];

    return (
        <Card>
            <CardHeader>
                <div className="flex justify-between items-center">
                    <div className="space-y-1">
                        <CardTitle className="text-lg">参考资料 (可选)</CardTitle>
                        <CardDescription>用于 AI 生成任务引导</CardDescription>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                {isLoading ? (
                    <div className="text-center py-4 text-muted-foreground">加载中...</div>
                ) : readyDocs.length === 0 ? (
                    <div className="text-center py-6 bg-muted/20 rounded-lg text-muted-foreground text-sm">
                        暂无可用教学资料
                        <br />
                        <a href="/inventory" className="text-primary underline mt-1 inline-block">
                            前往知识库上传
                        </a>
                    </div>
                ) : (
                    <div className="space-y-2">
                        <div
                            className={cn(
                                "flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors",
                                selectedDocId === null ? "bg-accent/50 border-primary" : "hover:bg-accent/10"
                            )}
                            onClick={() => onSelect(null)}
                        >
                            <div className={cn("h-4 w-4 rounded-full border border-primary", selectedDocId === null && "bg-primary")} />
                            <span className="text-sm font-medium">不使用参考资料（纯手动/仅依据课标）</span>
                        </div>

                        {readyDocs.map((doc: any) => (
                            <div
                                key={doc.id}
                                className={cn(
                                    "flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors",
                                    selectedDocId === doc.id ? "bg-accent/50 border-primary" : "hover:bg-accent/10"
                                )}
                                onClick={() => onSelect(doc.id)}
                            >
                                <div className={cn("h-4 w-4 rounded-full border border-primary", selectedDocId === doc.id && "bg-primary")} />
                                <span className="text-sm font-medium">{doc.filename}</span>
                                <span className="text-xs text-muted-foreground ml-auto">
                                    {new Date(doc.upload_date).toLocaleDateString()}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
