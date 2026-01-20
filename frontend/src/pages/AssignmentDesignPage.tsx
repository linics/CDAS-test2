import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { assignmentsApi, subjectsApi, apiClient } from '../lib/api';
import type { AssignmentCreate } from '../lib/api';

// 参考资料选择组件
const ReferenceDocumentsSection: React.FC = () => {
    const { data: documents, isLoading } = useQuery<any[]>({
        queryKey: ['documents'],
        queryFn: async () => {
            const res = await apiClient.get('/api/documents');
            return res.data;
        }
    });

    const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
    const readyDocs = documents?.filter(d => d.status === 'ready') || [];

    return (
        <section className="bg-white p-6 rounded-xl border space-y-4">
            <div className="flex justify-between items-center border-b pb-2">
                <h2 className="text-lg font-semibold text-gray-800">参考资料 (可选)</h2>
                <span className="text-xs text-gray-400">用于 AI 生成任务引导</span>
            </div>

            <p className="text-sm text-gray-500">
                选择您上传的教学设计文档，系统将基于该文档内容生成更贴合需求的任务引导。
            </p>

            {isLoading ? (
                <div className="text-center py-4 text-gray-400">加载中...</div>
            ) : readyDocs.length === 0 ? (
                <div className="text-center py-6 bg-gray-50 rounded-lg text-gray-400 text-sm">
                    暂无可用教学资料
                    <br />
                    <a href="/inventory" className="text-blue-600 underline mt-1 inline-block">
                        前往知识库上传
                    </a>
                </div>
            ) : (
                <div className="space-y-2">
                    <label className="flex items-center gap-2 p-3 border rounded-lg hover:bg-gray-50 cursor-pointer">
                        <input
                            type="radio"
                            name="ref_doc"
                            checked={selectedDocId === null}
                            onChange={() => setSelectedDocId(null)}
                            className="h-4 w-4 text-blue-600"
                        />
                        <span className="text-gray-700">不使用参考资料（纯手动 / 仅依据课标）</span>
                    </label>
                    {readyDocs.map((doc: any) => (
                        <label
                            key={doc.id}
                            className={`flex items-center gap-2 p-3 border rounded-lg hover:bg-gray-50 cursor-pointer ${selectedDocId === doc.id ? 'border-blue-500 bg-blue-50' : ''}`}
                        >
                            <input
                                type="radio"
                                name="ref_doc"
                                checked={selectedDocId === doc.id}
                                onChange={() => setSelectedDocId(doc.id)}
                                className="h-4 w-4 text-blue-600"
                            />
                            <span className="text-gray-700">{doc.filename}</span>
                            <span className="text-xs text-gray-400 ml-auto">
                                {new Date(doc.upload_date).toLocaleDateString()}
                            </span>
                        </label>
                    ))}
                </div>
            )}
        </section>
    );
};

const AssignmentDesignPage: React.FC = () => {
    const { id } = useParams();
    const isEditMode = !!id;
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    // 表单状态
    const [formData, setFormData] = useState<Partial<AssignmentCreate>>({
        title: '',
        topic: '',
        description: '',
        school_stage: 'middle',
        grade: 7,
        main_subject_id: 0,
        related_subject_ids: [],
        assignment_type: 'inquiry',
        inquiry_depth: 'intermediate',
        submission_mode: 'phased',
        duration_weeks: 2,
        practical_subtype: undefined,
        inquiry_subtype: 'literature',
    });
    const [aiPreview, setAiPreview] = useState<{
        objectives_json: Record<string, any>;
        phases_json: any[];
        rubric_json: Record<string, any>;
    } | null>(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isGeneratingSteps, setIsGeneratingSteps] = useState(false);

    // 获取学科列表
    const { data: subjectsData } = useQuery({
        queryKey: ['subjects'],
        queryFn: () => subjectsApi.list(),
    });

    // 如果是编辑模式，获取作业详情
    const { data: assignmentData } = useQuery({
        queryKey: ['assignment', id],
        queryFn: () => assignmentsApi.getById(Number(id)),
        enabled: isEditMode,
    });

    const flowData = isEditMode ? assignmentData?.data : aiPreview;

    // 初始化表单数据
    useEffect(() => {
        if (assignmentData && assignmentData.data) {
            const d = assignmentData.data;
            setFormData({
                title: d.title,
                topic: d.topic,
                description: d.description,
                school_stage: d.school_stage as any,
                grade: d.grade,
                main_subject_id: d.main_subject_id,
                related_subject_ids: d.related_subject_ids,
                assignment_type: d.assignment_type as any,
                inquiry_depth: d.inquiry_depth as any,
                submission_mode: d.submission_mode as any,
                duration_weeks: d.duration_weeks,
                practical_subtype: d.practical_subtype as any,
                inquiry_subtype: d.inquiry_subtype as any,
            });
        }
    }, [assignmentData]);

    // 创建/更新 Mutation
    const saveMutation = useMutation({
        mutationFn: (data: AssignmentCreate) => {
            if (isEditMode) {
                return assignmentsApi.update(Number(id), data);
            } else {
                return assignmentsApi.create(data);
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['assignments'] });
            navigate('/assignments');
        },
        onError: (err: any) => {
            alert(`保存失败: ${err.response?.data?.detail || err.message}`);
        }
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        // 简单验证
        if (!formData.title || !formData.main_subject_id) {
            alert('请填写必填项');
            return;
        }
        const payload: Partial<AssignmentCreate> = { ...formData };
        if (aiPreview) {
            payload.objectives_json = aiPreview.objectives_json;
            payload.phases_json = aiPreview.phases_json;
            payload.rubric_json = aiPreview.rubric_json;
        }
        saveMutation.mutate(payload as AssignmentCreate);
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setFormData(prev => {
            if (name === 'school_stage') {
                const nextStage = value as 'primary' | 'middle';
                let nextGrade = prev.grade;
                if (nextStage === 'primary' && nextGrade > 6) {
                    nextGrade = 6;
                }
                if (nextStage === 'middle' && nextGrade < 7) {
                    nextGrade = 7;
                }
                return {
                    ...prev,
                    school_stage: nextStage,
                    grade: nextGrade,
                };
            }
            return {
                ...prev,
                [name]: (name === 'grade' || name === 'duration_weeks' || name === 'main_subject_id')
                    ? Number(value)
                    : value,
            };
        });
    };

    const handleMultiSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const options = e.target.options;
        const value: number[] = [];
        for (let i = 0, l = options.length; i < l; i++) {
            if (options[i].selected) {
                value.push(Number(options[i].value));
            }
        }
        setFormData(prev => ({ ...prev, related_subject_ids: value }));
    };

    const handleAIPreview = async () => {
        if (!formData.title || !formData.topic || !formData.main_subject_id) {
            alert('请先填写标题、主题和主导学科');
            return;
        }
        setIsGenerating(true);
        try {
            const res = await assignmentsApi.preview(formData as AssignmentCreate);
            setAiPreview(res.data);
        } catch (err: any) {
            alert(`AI 预览失败: ${err.response?.data?.detail || err.message}`);
        } finally {
            setIsGenerating(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-8 pb-12">
            <div className="flex items-center gap-4 border-b pb-4">
                <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-800">
                    &larr; 返回
                </button>
                <h1 className="text-2xl font-bold text-gray-900">
                    {isEditMode ? '编辑作业' : '创建新作业'}
                </h1>
            </div>

            <form onSubmit={handleSubmit} className="space-y-8">

                {/* 基本信息 */}
                <section className="bg-white p-6 rounded-xl border space-y-4">
                    <h2 className="text-lg font-semibold text-gray-800 border-b pb-2">基本信息</h2>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-1">
                            <label className="block text-sm font-medium text-gray-700">作业标题 *</label>
                            <input
                                name="title"
                                value={formData.title}
                                onChange={handleChange}
                                className="w-full border rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 outline-none"
                                required
                            />
                        </div>
                        <div className="space-y-1">
                            <label className="block text-sm font-medium text-gray-700">探究主题 *</label>
                            <input
                                name="topic"
                                value={formData.topic}
                                onChange={handleChange}
                                className="w-full border rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 outline-none"
                                placeholder="例如：气候变化与农业"
                                required
                            />
                        </div>
                    </div>

                    <div className="space-y-1">
                        <label className="block text-sm font-medium text-gray-700">作业描述</label>
                        <textarea
                            name="description"
                            value={formData.description}
                            onChange={handleChange}
                            rows={3}
                            className="w-full border rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="space-y-1">
                            <label className="block text-sm font-medium text-gray-700">学段</label>
                            <select
                                name="school_stage"
                                value={formData.school_stage}
                                onChange={handleChange}
                                className="w-full border rounded-lg p-2.5"
                            >
                                <option value="primary">小学</option>
                                <option value="middle">初中</option>
                            </select>
                        </div>
                        <div className="space-y-1">
                            <label className="block text-sm font-medium text-gray-700">年级</label>
                            <select
                                name="grade"
                                value={formData.grade}
                                onChange={handleChange}
                                className="w-full border rounded-lg p-2.5"
                            >
                                {(formData.school_stage === 'middle'
                                    ? [7, 8, 9]
                                    : [1, 2, 3, 4, 5, 6]
                                ).map(g => (
                                    <option key={g} value={g}>
                                        {formData.school_stage === 'middle' ? `初中${g - 6}` : `小学${g}`}年级
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="space-y-1">
                            <label className="block text-sm font-medium text-gray-700">时长 (周)</label>
                            <input
                                type="number"
                                name="duration_weeks"
                                value={formData.duration_weeks}
                                onChange={handleChange}
                                min={1}
                                className="w-full border rounded-lg p-2.5"
                            />
                        </div>
                    </div>
                </section>

                {/* 学科设置 */}
                <section className="bg-white p-6 rounded-xl border space-y-4">
                    <h2 className="text-lg font-semibold text-gray-800 border-b pb-2">学科设置</h2>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-1">
                            <label className="block text-sm font-medium text-gray-700">主导学科 *</label>
                            <select
                                name="main_subject_id"
                                value={formData.main_subject_id}
                                onChange={handleChange}
                                className="w-full border rounded-lg p-2.5"
                                required
                            >
                                <option value={0}>请选择</option>
                                {subjectsData?.data.subjects.map((s: any) => (
                                    <option key={s.id} value={s.id}>{s.name} ({s.code})</option>
                                ))}
                            </select>
                        </div>

                        <div className="space-y-1">
                            <label className="block text-sm font-medium text-gray-700">关联学科 (按住Ctrl多选)</label>
                            <select
                                multiple
                                value={formData.related_subject_ids?.map(String)}
                                onChange={handleMultiSelect}
                                className="w-full border rounded-lg p-2.5 h-32"
                            >
                                {subjectsData?.data.subjects.map((s: any) => (
                                    <option key={s.id} value={s.id}>{s.name}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                </section>

                {/* 参考资料（用于 AI 生成） */}
                <ReferenceDocumentsSection />

                {!isEditMode && (
                    <section className="bg-white p-6 rounded-xl border space-y-4">
                        <div className="flex justify-between items-center border-b pb-2">
                            <h2 className="text-lg font-semibold text-gray-800">AI 预览</h2>
                            <button
                                type="button"
                                onClick={handleAIPreview}
                                disabled={isGenerating}
                                className="text-sm bg-blue-100 text-blue-700 px-3 py-1 rounded-full hover:bg-blue-200 transition disabled:opacity-60"
                            >
                                {isGenerating ? '生成中...' : 'AI 自动生成'}
                            </button>
                        </div>

                        {aiPreview ? (
                            <div className="space-y-4 text-sm text-gray-600">
                                <div>
                                    <div className="font-semibold text-gray-800">学习目标</div>
                                    <ul className="list-disc pl-5 space-y-1">
                                        <li>知识与技能: {aiPreview.objectives_json?.knowledge}</li>
                                        <li>过程与方法: {aiPreview.objectives_json?.process}</li>
                                        <li>情感态度: {aiPreview.objectives_json?.emotion}</li>
                                    </ul>
                                </div>
                                <div>
                                    <div className="font-semibold text-gray-800">任务阶段</div>
                                    <ol className="list-decimal pl-5 space-y-1">
                                        {(aiPreview.phases_json || []).map((phase: any, idx: number) => (
                                            <li key={idx}>{phase.name}</li>
                                        ))}
                                    </ol>
                                </div>
                                <div>
                                    <div className="font-semibold text-gray-800">评价量表</div>
                                    <ul className="list-disc pl-5 space-y-1">
                                        {(aiPreview.rubric_json?.dimensions || []).map((dim: any, idx: number) => (
                                            <li key={idx}>
                                                {dim.name} ({dim.weight})
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        ) : (
                            <div className="text-center py-6 text-gray-400 text-sm">
                                点击“AI 自动生成”预览任务目标、阶段和量表。
                            </div>
                        )}
                    </section>
                )}

                {/* 模式选择 */}
                <section className="bg-white p-6 rounded-xl border space-y-4">
                    <h2 className="text-lg font-semibold text-gray-800 border-b pb-2">作业模式与类型</h2>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="space-y-1">
                            <label className="block text-sm font-medium text-gray-700">作业类型</label>
                            <select
                                name="assignment_type"
                                value={formData.assignment_type}
                                onChange={handleChange}
                                className="w-full border rounded-lg p-2.5"
                            >
                                <option value="practical">实践性作业</option>
                                <option value="inquiry">探究性作业</option>
                                <option value="project">项目式作业</option>
                            </select>
                        </div>

                        <div className="space-y-1">
                            <label className="block text-sm font-medium text-gray-700">子类型</label>
                            {formData.assignment_type === 'practical' ? (
                                <select
                                    name="practical_subtype"
                                    value={formData.practical_subtype}
                                    onChange={handleChange}
                                    className="w-full border rounded-lg p-2.5"
                                >
                                    <option value="visit">参观考察型</option>
                                    <option value="simulation">模拟表演型</option>
                                    <option value="observation">观察体验型</option>
                                </select>
                            ) : formData.assignment_type === 'inquiry' ? (
                                <select
                                    name="inquiry_subtype"
                                    value={formData.inquiry_subtype}
                                    onChange={handleChange}
                                    className="w-full border rounded-lg p-2.5"
                                >
                                    <option value="literature">文献探究</option>
                                    <option value="survey">调查探究</option>
                                    <option value="experiment">实验探究</option>
                                </select>
                            ) : (
                                <div className="p-2.5 text-gray-400 text-sm">无子类型</div>
                            )}
                        </div>

                        <div className="space-y-1">
                            <label className="block text-sm font-medium text-gray-700">探究深度</label>
                            <select
                                name="inquiry_depth"
                                value={formData.inquiry_depth}
                                onChange={handleChange}
                                className="w-full border rounded-lg p-2.5"
                            >
                                <option value="basic">基础探究</option>
                                <option value="intermediate">中等探究</option>
                                <option value="deep">深度探究</option>
                            </select>
                        </div>
                    </div>

                    <div className="space-y-1">
                        <label className="block text-sm font-medium text-gray-700">提交模式</label>
                        <div className="flex gap-4 pt-1">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="radio"
                                    name="submission_mode"
                                    value="phased"
                                    checked={formData.submission_mode === 'phased'}
                                    onChange={handleChange}
                                />
                                <span>过程性提交 (分阶段)</span>
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="radio"
                                    name="submission_mode"
                                    value="once"
                                    checked={formData.submission_mode === 'once'}
                                    onChange={handleChange}
                                />
                                <span>一次性提交</span>
                            </label>
                        </div>
                    </div>
                </section>

                {/* 任务流程设置 (仅在编辑模式下可用) */}
                <section className="bg-white p-6 rounded-xl border space-y-4">
                        <div className="flex justify-between items-center border-b pb-2">
                            <h2 className="text-lg font-semibold text-gray-800">任务流程设置</h2>
                            <button
                                type="button"
                                onClick={() => {
                                    if (isEditMode) {
                                        if (confirm("确定要生成新的流程吗？这将覆盖现有流程。")) {
                                        setIsGeneratingSteps(true);
                                        assignmentsApi.generateSteps(Number(id))
                                            .then((res: any) => {
                                                const phases = res?.data?.phases;
                                                if (phases) {
                                                    queryClient.setQueryData(['assignment', id], (old: any) => {
                                                        if (!old?.data) return old;
                                                        return {
                                                            ...old,
                                                            data: {
                                                                ...old.data,
                                                                phases_json: phases,
                                                            },
                                                        };
                                                    });
                                                }
                                                alert("生成成功！");
                                                queryClient.invalidateQueries({ queryKey: ['assignment', id] });
                                            })
                                            .catch((err: any) => {
                                                alert(`生成失败: ${err.message}`);
                                            })
                                            .finally(() => {
                                                setIsGeneratingSteps(false);
                                            });
                                    }
                                    } else {
                                        handleAIPreview();
                                    }
                                }}
                                disabled={isEditMode ? isGeneratingSteps : isGenerating}
                                className="text-sm bg-purple-100 text-purple-700 px-3 py-1 rounded-full hover:bg-purple-200 transition flex items-center gap-1 disabled:opacity-60"
                            >
                                <span>*</span> {(isEditMode ? isGeneratingSteps : isGenerating) ? '生成中...' : 'AI 生成任务引导'}
                            </button>
                        </div>

                        <div className="space-y-4">
                            {flowData?.phases_json ? (
                                <div className="space-y-4">
                                    {flowData.objectives_json ? (
                                        <div className="border rounded-xl p-4 bg-white">
                                            <div className="font-semibold text-gray-900 mb-2">学习目标</div>
                                            <div className="text-sm text-gray-700 space-y-2">
                                                <div>
                                                    <span className="font-medium text-gray-800">知识与技能：</span>
                                                    <span className="break-words">{flowData.objectives_json.knowledge}</span>
                                                </div>
                                                <div>
                                                    <span className="font-medium text-gray-800">过程与方法：</span>
                                                    <span className="break-words">{flowData.objectives_json.process}</span>
                                                </div>
                                                <div>
                                                    <span className="font-medium text-gray-800">情感态度：</span>
                                                    <span className="break-words">{flowData.objectives_json.emotion}</span>
                                                </div>
                                            </div>
                                        </div>
                                    ) : null}
                                    {(flowData.phases_json as any[]).map((phase, idx) => {
                                        const phaseOrder = typeof phase?.order === 'number' ? phase.order : idx + 1;
                                        const phaseTitle = phase?.title || phase?.name || `阶段 ${phaseOrder}`;
                                        const phaseName = phase?.title && phase?.name && phase.title !== phase.name
                                            ? phase.name
                                            : '';
                                        const phaseSteps = Array.isArray(phase?.steps) ? phase.steps : [];
                                        return (
                                            <div key={idx} className="border rounded-xl p-4 bg-gray-50">
                                                <div className="flex items-center justify-between">
                                                    <div className="font-semibold text-gray-900">
                                                        阶段 {phaseOrder}：{phaseTitle}
                                                    </div>
                                                    <div className="text-xs text-gray-400">
                                                        {phaseSteps.length || 0} 步
                                                    </div>
                                                </div>
                                                {phaseName ? (
                                                    <div className="text-xs text-gray-500 mt-1">模板名称：{phaseName}</div>
                                                ) : null}
                                                <div className="mt-3 space-y-3">
                                                    {phaseSteps.map((step: any, sIdx: number) => {
                                                        const stepName = (step?.name || step?.title || '').trim?.() || '';
                                                        const stepContent = (step?.content || '').trim?.() || '';
                                                        const stepDescription = (step?.description || '').trim?.() || '';
                                                        const primaryText = stepContent || stepDescription || stepName || `步骤 ${sIdx + 1}`;
                                                        const checkpoints = Array.isArray(step?.checkpoints) ? step.checkpoints : [];
                                                        const showName = stepName && stepName !== primaryText;
                                                        const showContent = stepContent && stepContent !== primaryText;
                                                        const showDescription = stepDescription
                                                            && stepDescription !== primaryText
                                                            && stepDescription !== stepContent;
                                                        return (
                                                            <div key={sIdx} className="bg-white rounded-lg border p-3">
                                                                <div className="text-sm font-medium text-gray-800">
                                                                    {sIdx + 1}. {primaryText}
                                                                </div>
                                                                {showContent ? (
                                                                    <div className="text-sm text-gray-600 leading-6 mt-1 break-words">
                                                                        内容：{stepContent}
                                                                    </div>
                                                                ) : null}
                                                                {showDescription ? (
                                                                    <div className="text-sm text-gray-600 leading-6 mt-1 break-words">
                                                                        描述：{stepDescription}
                                                                    </div>
                                                                ) : null}
                                                                {showName ? (
                                                                    <div className="text-xs text-gray-500 mt-1 break-words">
                                                                        名称：{stepName}
                                                                    </div>
                                                                ) : null}
                                                                {checkpoints.length > 0 ? (
                                                                    <div className="mt-2">
                                                                        <div className="text-xs text-gray-400 mb-1">检查点</div>
                                                                        <div className="space-y-1">
                                                                            {checkpoints.map((cp: any, cIdx: number) => (
                                                                                <div key={cIdx} className="text-xs text-gray-600 break-words">
                                                                                    <span className="inline-block bg-gray-100 px-2 py-0.5 rounded-full mr-2">
                                                                                        {cp?.evidence_type || 'text'}
                                                                                    </span>
                                                                                    {cp?.content}
                                                                                </div>
                                                                            ))}
                                                                        </div>
                                                                    </div>
                                                                ) : null}
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            ) : (
                                <div className="text-center py-8 text-gray-400 border-2 border-dashed rounded-lg">
                                    暂无任务流程，请点击上方按钮生成。
                                </div>
                            )}
                        </div>
                    </section>
                )}

                {/* 操作栏 */}
                <div className="flex justify-end gap-4 pt-4">
                    <button
                        type="button"
                        onClick={() => navigate('/assignments')}
                        className="px-6 py-2 border rounded-lg hover:bg-gray-50 transition text-gray-700"
                    >
                        取消
                    </button>
                    <button
                        type="submit"
                        disabled={saveMutation.isPending}
                        className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium shadow-md disabled:opacity-70"
                    >
                        {saveMutation.isPending ? '保存中...' : '保存作业设计'}
                    </button>
                </div>

            </form>
        </div>
    );
};

export default AssignmentDesignPage;
