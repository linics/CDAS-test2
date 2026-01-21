import { Button } from "../../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";

export function AIPreviewSection({
    aiPreview,
    loading,
    onGenerate
}: {
    aiPreview: any,
    loading: boolean,
    onGenerate: () => void
}) {
    return (
        <Card className="border-primary/20 bg-primary/5">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg text-primary">AI 预览</CardTitle>
                <Button
                    variant="default" // Changed from outline to default for better visibility
                    size="sm"
                    onClick={onGenerate}
                    disabled={loading}
                    className="gap-2"
                >
                    {loading ? (
                        <span className="animate-spin">⏳</span>
                    ) : "✨"}
                    {loading ? '生成中...' : '即刻生成'}
                </Button>
            </CardHeader>
            <CardContent>
                {aiPreview ? (
                    <div className="space-y-6 text-sm">
                        {/* 学习目标 */}
                        <div className="space-y-2 animate-slide-up">
                            <h4 className="font-semibold text-foreground flex items-center gap-2">
                                <Badge variant="outline">Target</Badge> 学习目标
                            </h4>
                            <ul className="grid gap-2 pl-2 border-l-2 border-primary/20 ml-1">
                                <li className="grid grid-cols-[80px_1fr] gap-2">
                                    <span className="text-muted-foreground">知识与技能:</span>
                                    <span>{aiPreview.objectives_json?.knowledge}</span>
                                </li>
                                <li className="grid grid-cols-[80px_1fr] gap-2">
                                    <span className="text-muted-foreground">过程与方法:</span>
                                    <span>{aiPreview.objectives_json?.process}</span>
                                </li>
                                <li className="grid grid-cols-[80px_1fr] gap-2">
                                    <span className="text-muted-foreground">情感态度:</span>
                                    <span>{aiPreview.objectives_json?.emotion}</span>
                                </li>
                            </ul>
                        </div>

                        {/* 任务阶段 */}
                        <div className="space-y-2 animate-slide-up" style={{ animationDelay: "0.1s" }}>
                            <h4 className="font-semibold text-foreground flex items-center gap-2">
                                <Badge variant="outline">Process</Badge> 任务阶段
                            </h4>
                            <div className="space-y-2 pl-1">
                                {(aiPreview.phases_json || []).map((phase: any, idx: number) => (
                                    <div key={idx} className="flex items-center gap-2 p-2 bg-background/50 rounded-md border">
                                        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                                            {idx + 1}
                                        </span>
                                        <span>{phase.name}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* 评价量表 */}
                        <div className="space-y-2 animate-slide-up" style={{ animationDelay: "0.2s" }}>
                            <h4 className="font-semibold text-foreground flex items-center gap-2">
                                <Badge variant="outline">Rubric</Badge> 评价量表
                            </h4>
                            <div className="flex flex-wrap gap-2 pl-1">
                                {(aiPreview.rubric_json?.dimensions || []).map((dim: any, idx: number) => (
                                    <Badge key={idx} variant="secondary">
                                        {dim.name} ({dim.weight})
                                    </Badge>
                                ))}
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="text-center py-8 text-muted-foreground border-2 border-dashed rounded-lg bg-background/50">
                        <p>点击上方按钮，AI 将为您自动生成任务目标、阶段和量表。</p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
