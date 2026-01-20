import React, { useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Upload, Loader2 } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { cn } from '@/lib/utils';

interface FileUploadProps {
    className?: string;
    onUploadSuccess?: () => void;
}

export function FileUpload({ className, onUploadSuccess }: FileUploadProps) {
    const queryClient = useQueryClient();
    const fileInputRef = React.useRef<HTMLInputElement>(null);
    const [isDragOver, setIsDragOver] = React.useState(false);

    const uploadMutation = useMutation({
        mutationFn: async (file: File) => {
            const formData = new FormData();
            formData.append('file', file);
            const res = await apiClient.post('/api/documents/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            return res.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            onUploadSuccess?.();
        },
        onError: (err) => {
            console.error("Upload failed", err);
            alert("上传失败。详情请查看控制台。");
        }
    });

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            uploadMutation.mutate(e.target.files[0]);
        }
        // Reset value to allow uploading valid file again if needed
        e.target.value = '';
    };

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            uploadMutation.mutate(e.dataTransfer.files[0]);
        }
    }, [uploadMutation]);

    return (
        <div
            className={cn(
                "border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer flex flex-col items-center justify-center gap-2",
                isDragOver ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:border-blue-400 hover:bg-gray-50",
                className
            )}
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
        >
            <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept=".pdf,.docx"
                onChange={handleFileChange}
            />
            {uploadMutation.isPending ? (
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            ) : (
                <Upload className="h-8 w-8 text-gray-400" />
            )}
            <div className="text-sm text-gray-600 font-medium">
                {uploadMutation.isPending ? "正在上传......" : "点击或拖拽文件以上传"}
            </div>
            <div className="text-xs text-gray-400">PDF 或 Word 文档</div>
        </div>
    );
}
