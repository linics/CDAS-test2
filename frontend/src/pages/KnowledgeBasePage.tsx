import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, CheckCircle2, BookOpen, FileText, Upload, AlertCircle } from 'lucide-react';

// 系统内置课标学科列表
const BUILT_IN_SUBJECTS = [
    { code: '00', name: '课程方案（总纲）' },
    { code: '01', name: '道德与法治' },
    { code: '02', name: '语文' },
    { code: '03', name: '历史' },
    { code: '04', name: '英语' },
    { code: '05', name: '地理' },
    { code: '06', name: '科学' },
    { code: '07', name: '物理' },
    { code: '08', name: '生物学' },
    { code: '09', name: '信息科技' },
    { code: '10', name: '体育与健康' },
    { code: '11', name: '艺术' },
    { code: '12', name: '劳动' },
    { code: '13', name: '数学' },
    { code: '14', name: '化学' },
];

interface CustomDocument {
    id: number;
    filename: string;
    status: 'uploaded' | 'indexing' | 'ready' | 'failed';
    upload_date: string;
    error_msg?: string;
    source?: 'user' | 'system';
}

export default function KnowledgeBasePage() {
    const queryClient = useQueryClient();
    const [showUpload, setShowUpload] = useState(false);

    // 获取用户上传的文档列表
    const { data: documents, isLoading } = useQuery<CustomDocument[]>({
        queryKey: ['documents'],
        queryFn: async () => {
            const res = await apiClient.get('/api/documents');
            return res.data;
        },
        refetchInterval: (query) => {
            const data = query.state.data as CustomDocument[] | undefined;
            if (data?.some(d => d.status === 'indexing' || d.status === 'uploaded')) {
                return 3000;
            }
            return false;
        }
    });

    const isBuiltInDocument = (doc: CustomDocument) =>
        doc.source === 'system' ||
        /^W0\d+\.docx$/i.test(doc.filename) ||
        /^0\d_.*\.docx$/i.test(doc.filename);

    const builtInDocs = documents?.filter(isBuiltInDocument) || [];
    const customDocs = documents?.filter(doc => !isBuiltInDocument(doc)) || [];

    const readyCount = customDocs.filter(d => d.status === 'ready').length;
    const processingCount = customDocs.filter(d => d.status === 'indexing' || d.status === 'uploaded').length;

    const deleteMutation = useMutation({
        mutationFn: (documentId: number) => apiClient.delete(`/api/documents/${documentId}`),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
        },
        onError: (err: any) => {
            alert(`删除失败: ${err.response?.data?.detail || err.message}`);
        },
    });

    const handleDelete = (documentId: number, filename: string) => {
        if (window.confirm(`确定要删除「${filename}」吗？此操作无法撤销。`)) {
            deleteMutation.mutate(documentId);
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            {/* 页面标题 */}
            <div>
                <h1 className="text-2xl font-bold text-gray-900">知识库</h1>
                <p className="text-gray-500 mt-1">
                    系统知识库为作业设计提供课程标准和教学资料支持。
                </p>
            </div>

            {/* 系统内置知识库 */}
            <Card className="border-green-200 bg-green-50/50">
                <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-green-800">
                        <BookOpen className="h-5 w-5" />
                        系统内置课程标准
                        <span className="ml-auto text-sm font-normal bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                            已就绪 ✓
                        </span>
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-sm text-green-700 mb-4">
                        已导入《义务教育课程标准（2022年版）》共 15 个学科文档，作为作业设计的核心知识基础。
                    </p>
                    <div className="flex flex-wrap gap-2">
                        {BUILT_IN_SUBJECTS.map(subject => (
                            <span
                                key={subject.code}
                                className="text-xs bg-white text-green-700 px-2 py-1 rounded border border-green-200"
                            >
                                {subject.name}
                            </span>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* 自定义教学资料 */}
            <Card>
                <CardHeader className="pb-3">
                    <div className="flex justify-between items-start">
                        <CardTitle className="flex items-center gap-2">
                            <FileText className="h-5 w-5 text-blue-600" />
                            我的教学资料
                            {readyCount > 0 && (
                                <span className="text-sm font-normal bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
                                    已入库 {readyCount} 份
                                </span>
                            )}
                        </CardTitle>
                        <Button
                            size="sm"
                            onClick={() => setShowUpload(!showUpload)}
                            className="gap-1"
                        >
                            <Upload className="h-4 w-4" />
                            上传资料
                        </Button>
                    </div>
                </CardHeader>
                <CardContent className="space-y-4">
                    <p className="text-sm text-gray-500">
                        上传您的教学设计文档（PDF/Word），系统将自动解析并纳入知识库，用于生成更贴合您教学需求的任务引导。
                    </p>

                    {/* 上传区域 */}
                    {showUpload && (
                        <div className="border-2 border-dashed border-blue-200 rounded-lg p-6 bg-blue-50/50">
                            <FileUpload onUploadSuccess={() => {
                                queryClient.invalidateQueries({ queryKey: ['documents'] });
                                setShowUpload(false);
                            }} />
                            <p className="text-xs text-center text-gray-500 mt-3">
                                支持 PDF、Word 文档，单文件最大 50MB
                            </p>
                        </div>
                    )}

                    {/* 已上传资料列表 */}
                    {isLoading ? (
                        <div className="flex justify-center py-8">
                            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                        </div>
                    ) : customDocs.length > 0 ? (
                        <div className="space-y-3">
                            {customDocs.map(doc => (
                                <div
                                    key={doc.id}
                                    className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg"
                                >
                                    <div className="h-10 w-10 bg-white rounded flex items-center justify-center border">
                                        <FileText className="h-5 w-5 text-gray-400" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="font-medium text-gray-900 truncate">
                                            {doc.filename}
                                        </div>
                                        <div className="text-xs text-gray-500">
                                            导入时间：{new Date(doc.upload_date).toLocaleDateString()}
                                        </div>
                                    </div>
                                    <div>
                                        {doc.status === 'ready' ? (
                                            <span className="flex items-center gap-1 text-sm text-green-600">
                                                <CheckCircle2 className="h-4 w-4" />
                                                已入库
                                            </span>
                                        ) : doc.status === 'failed' ? (
                                            <span className="flex items-center gap-1 text-sm text-red-600">
                                                <AlertCircle className="h-4 w-4" />
                                                处理失败
                                            </span>
                                        ) : (
                                            <span className="flex items-center gap-1 text-sm text-amber-600">
                                                <Loader2 className="h-4 w-4 animate-spin" />
                                                处理中
                                            </span>
                                        )}
                                    </div>
                                    <div className="ml-auto">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => handleDelete(doc.id, doc.filename)}
                                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                        >
                                            删除
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-8 text-gray-400 border-2 border-dashed rounded-lg">
                            暂无自定义教学资料
                            <br />
                            <span className="text-sm">点击上方按钮上传您的教学设计文档</span>
                        </div>
                    )}

                    {builtInDocs.length > 0 && (
                        <div className="text-xs text-gray-400">
                            系统内置文档已归入“系统内置课程标准”，不显示在此列表（已隐藏 {builtInDocs.length} 份）。
                        </div>
                    )}

                    {/* 处理中提示 */}
                    {processingCount > 0 && (
                        <div className="flex items-center gap-2 text-sm text-amber-600 bg-amber-50 p-3 rounded-lg">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            {processingCount} 份文档正在处理中，请稍候...
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* 使用提示 */}
            <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-600">
                <strong className="text-gray-800">💡 如何使用知识库？</strong>
                <ul className="mt-2 space-y-1 list-disc list-inside">
                    <li>在「作业设计」页面创建新作业时，可以选择参考您上传的教学资料</li>
                    <li>系统会结合课程标准和您的教学资料，生成更贴合需求的任务引导</li>
                    <li>已入库的资料会持续支持后续所有作业的 AI 生成功能</li>
                </ul>
            </div>
        </div>
    );
}
