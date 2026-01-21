import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useForm, FormProvider } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { assignmentsApi } from "../../lib/api";
import { assignmentFormSchema, type AssignmentFormValues } from "./schema";

import { BasicInfoForm } from "./components/BasicInfoForm";
import { SubjectSelection } from "./components/SubjectSelection";
import { ReferenceMaterial } from "./components/ReferenceMaterial";
import { AIPreviewSection } from "./components/AIPreviewSection";
import { ProcessDesigner } from "./components/ProcessDesigner";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";


export default function AssignmentDesign() {
    const { id } = useParams();
    const isEditMode = !!id;
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    // State for non-form data
    const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
    const [aiPreview, setAiPreview] = useState<any>(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isGeneratingSteps, setIsGeneratingSteps] = useState(false);

    // Form Initialization
    const methods = useForm<AssignmentFormValues>({
        resolver: zodResolver(assignmentFormSchema),
        defaultValues: {
            title: "",
            topic: "",
            related_subject_ids: [],
            school_stage: "middle",
            grade: 7,
            assignment_type: "inquiry",
            inquiry_depth: "intermediate",
            submission_mode: "phased",
            duration_weeks: 2,
        }
    });

    // Fetch Existing Data (Edit Mode)
    const { data: assignmentData } = useQuery({
        queryKey: ['assignment', id],
        queryFn: () => assignmentsApi.getById(Number(id)),
        enabled: isEditMode,
    });

    // Populate Form
    useEffect(() => {
        if (assignmentData?.data) {
            const d = assignmentData.data;
            // @ts-ignore
            methods.reset({
                ...d,
                related_subject_ids: d.related_subject_ids || [],
            });
            // Also set preview data if available, though usually stored in DB fields
            if (d.objectives_json || d.phases_json) {
                setAiPreview({
                    objectives_json: d.objectives_json,
                    phases_json: d.phases_json,
                    rubric_json: d.rubric_json
                });
            }
        }
    }, [assignmentData, methods]);

    // Mutations
    const saveMutation = useMutation({
        mutationFn: (data: any) => {
            const payload = {
                ...data,
                objectives_json: aiPreview?.objectives_json,
                phases_json: aiPreview?.phases_json,
                rubric_json: aiPreview?.rubric_json,
            };
            if (isEditMode) {
                return assignmentsApi.update(Number(id), payload);
            } else {
                return assignmentsApi.create(payload);
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['assignments'] });
            toast.success("作业保存成功！");
            navigate('/assignments');
        },
        onError: (err: any) => {
            toast.error(`保存失败: ${err.message}`);
        }
    });

    // Handlers
    const handleAIPreview = async () => {
        const values = methods.getValues();
        if (!values.title || !values.topic || !values.main_subject_id) {
            toast.warning("请先填写标题、主题和主导学科");
            return;
        }

        setIsGenerating(true);
        try {
            // Pass selectedDocId if needed by API in future, currently API might rely on other fields
            // The original code didn't transparently pass docId to preview? 
            // Ah, the original code collected it but `assignmentsApi.preview` takes `AssignmentCreate`.
            // Ensure specific fields are passed if the backend supports it.
            const res = await assignmentsApi.preview(values as any);
            setAiPreview(res.data);
            toast.success("AI 预览生成完成");
        } catch (err: any) {
            toast.error("生成失败，请重试");
        } finally {
            setIsGenerating(false);
        }
    };

    const handleGenerateSteps = async () => {
        if (!isEditMode) {
            handleAIPreview();
            return;
        }

        if (!confirm("确定要重新生成流程吗？这将覆盖现有数据。")) return;

        setIsGeneratingSteps(true);
        try {
            const res = await assignmentsApi.generateSteps(Number(id));
            const phases = res?.data?.phases;
            if (phases) {
                setAiPreview(prev => ({ ...prev, phases_json: phases }));
                toast.success("流程生成更新成功");
            }
        } catch (err: any) {
            toast.error("流程生成失败");
        } finally {
            setIsGeneratingSteps(false);
        }
    };

    const onSubmit = (data: AssignmentFormValues) => {
        saveMutation.mutate(data);
    };

    return (
        <div className="max-w-5xl mx-auto space-y-8 pb-20 animate-fade-in">
            <div className="flex items-center justify-between">
                <div className="space-y-1">
                    <h1 className="text-3xl font-bold tracking-tight">
                        {isEditMode ? '编辑作业设计' : '创建新作业'}
                    </h1>
                    <p className="text-muted-foreground">
                        利用 AI 大模型辅助设计跨学科探究性作业
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => navigate(-1)}>取消</Button>
                    <Button onClick={methods.handleSubmit(onSubmit as any)} disabled={saveMutation.isPending}>
                        {saveMutation.isPending ? '保存中...' : '保存设计'}
                    </Button>
                </div>
            </div>

            <FormProvider {...methods}>
                <form className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Left Column: Forms */}
                    <div className="lg:col-span-2 space-y-8">
                        <BasicInfoForm />
                        <SubjectSelection />

                        {/* Mode Selection can be inline or separate. For now included in BasicInfo or add a new one. 
                        The original had a specific section for "Assignment Type" etc.
                        Let's put it in a separate card here.
                    */}
                        <Card>
                            <CardHeader><CardTitle className="text-lg">模式与类型</CardTitle></CardHeader>
                            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium">作业类型</label>
                                    <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" {...methods.register("assignment_type")}>
                                        <option value="practical">实践性作业</option>
                                        <option value="inquiry">探究性作业</option>
                                        <option value="project">项目式作业</option>
                                    </select>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-sm font-medium">探究深度</label>
                                    <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" {...methods.register("inquiry_depth")}>
                                        <option value="basic">基础探究</option>
                                        <option value="intermediate">中等探究</option>
                                        <option value="deep">深度探究</option>
                                    </select>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-sm font-medium">提交模式</label>
                                    <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" {...methods.register("submission_mode")}>
                                        <option value="phased">过程性提交(分阶段)</option>
                                        <option value="once">一次性提交</option>
                                    </select>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Process Designer (Visible mostly in Edit Mode or after Preview) */}
                        {(isEditMode || aiPreview?.phases_json) && (
                            <ProcessDesigner
                                phases={aiPreview?.phases_json}
                                objectives={aiPreview?.objectives_json}
                                isEditMode={isEditMode}
                                onGenerate={handleGenerateSteps}
                                isGenerating={isGeneratingSteps}
                            />
                        )}
                    </div>

                    {/* Right Column: AI & Reference */}
                    <div className="space-y-6">
                        <ReferenceMaterial
                            selectedDocId={selectedDocId}
                            onSelect={setSelectedDocId}
                        />

                        {!isEditMode && (
                            <AIPreviewSection
                                aiPreview={aiPreview}
                                loading={isGenerating}
                                onGenerate={handleAIPreview}
                            />
                        )}

                        {/* Sticky Save Button for mobile/long pages */}
                        <div className="sticky top-24">
                            <Card className="bg-muted/30 border-dashed">
                                <CardContent className="pt-6">
                                    <Button className="w-full" size="lg" onClick={methods.handleSubmit(onSubmit as any)} disabled={saveMutation.isPending}>
                                        {saveMutation.isPending ? '保存中...' : '保存所有更改'}
                                    </Button>
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </form>
            </FormProvider>
        </div>
    );
}
