import { Button } from "../../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";

export function ProcessDesigner({
    phases,
    objectives,
    isEditMode,
    onGenerate,
    isGenerating
}: {
    phases: any[],
    objectives: any,
    isEditMode: boolean,
    onGenerate: () => void,
    isGenerating: boolean
}) {
    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div className="space-y-1">
                    <CardTitle className="text-lg">任务流程设置</CardTitle>
                    <CardDescription>查看或重新生成任务的具体流程</CardDescription>
                </div>
                <Button
                    variant="secondary"
                    size="sm"
                    onClick={onGenerate}
                    disabled={isGenerating}
                    className="gap-2"
                >
                    {isGenerating ? <span className="animate-spin">⏳</span> : "⚡"}
                    {isGenerating ? '生成中...' : (isEditMode ? '重新生成引导' : 'AI 生成引导')}
                </Button>
            </CardHeader>
            <CardContent className="space-y-6">
                {phases && phases.length > 0 ? (
                    <div className="space-y-4">
                        {/* Objectives Display if available from flowData context */}
                        {objectives && (
                            <div className="rounded-lg bg-muted/50 p-4 text-sm">
                                <div className="font-semibold mb-2">学习目标确认</div>
                                <div className="grid gap-1">
                                    <div><span className="font-medium">知识:</span> {objectives.knowledge}</div>
                                    <div><span className="font-medium">过程:</span> {objectives.process}</div>
                                    <div><span className="font-medium">情感:</span> {objectives.emotion}</div>
                                </div>
                            </div>
                        )}

                        {phases.map((phase, idx) => {
                            const phaseOrder = typeof phase?.order === 'number' ? phase.order : idx + 1;
                            const phaseTitle = phase?.title || phase?.name || `阶段 ${phaseOrder}`;
                            const phaseSteps = Array.isArray(phase?.steps) ? phase.steps : [];

                            return (
                                <div key={idx} className="border rounded-lg p-4 bg-card">
                                    <div className="flex items-center justify-between mb-3">
                                        <h4 className="font-semibold text-sm">
                                            阶段 {phaseOrder}：{phaseTitle}
                                        </h4>
                                        <Badge variant="outline">{phaseSteps.length} 步</Badge>
                                    </div>

                                    <div className="space-y-3">
                                        {phaseSteps.map((step: any, sIdx: number) => {
                                            const stepName = (step?.name || step?.title || '').trim?.() || '';
                                            const stepContent = (step?.content || '').trim?.() || '';
                                            const primaryText = stepContent || stepName || `步骤 ${sIdx + 1}`;

                                            return (
                                                <div key={sIdx} className="bg-background rounded-md border p-3 text-sm shadow-sm">
                                                    <div className="font-medium mb-1">{sIdx + 1}. {primaryText}</div>
                                                    {step.description && (
                                                        <div className="text-muted-foreground text-xs">{step.description}</div>
                                                    )}
                                                </div>
                                            )
                                        })}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <div className="text-center py-8 text-muted-foreground border-2 border-dashed rounded-lg">
                        暂无任务流程，请点击上方按钮生成。
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
