import { useFormContext, Controller } from "react-hook-form";
import { useQuery } from "@tanstack/react-query";
import { subjectsApi } from "../../../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Label } from "../../../components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from "../../../components/ui/select"; // Using Shadcn Select for main subject

export function SubjectSelection() {
    const { register, control } = useFormContext();

    const { data: subjectsData } = useQuery({
        queryKey: ['subjects'],
        queryFn: () => subjectsApi.list(),
    });

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-lg">学科设置</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label>主导学科 *</Label>
                        <Controller
                            control={control}
                            name="main_subject_id"
                            render={({ field }) => (
                                <Select onValueChange={(val) => field.onChange(Number(val))} value={String(field.value || '')}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="选择主导学科" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {subjectsData?.data.subjects.map((s: any) => (
                                            <SelectItem key={s.id} value={String(s.id)}>
                                                {s.name} ({s.code})
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            )}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label>关联学科 (按住Ctrl多选)</Label>
                        <select
                            multiple
                            className="flex h-32 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                            {...register("related_subject_ids")}
                        >
                            {subjectsData?.data.subjects.map((s: any) => (
                                <option key={s.id} value={s.id}>{s.name}</option>
                            ))}
                        </select>
                        <p className="text-xs text-muted-foreground mt-1">目前暂支持多选框原生交互</p>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
