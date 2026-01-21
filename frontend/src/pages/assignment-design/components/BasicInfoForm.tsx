import { useFormContext, Controller } from "react-hook-form";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Label } from "../../../components/ui/label";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from "../../../components/ui/select";

export function BasicInfoForm() {
    const { register, watch, control, formState: { errors } } = useFormContext();
    const schoolStage = watch("school_stage");

    const grades = schoolStage === 'middle' ? [7, 8, 9] : [1, 2, 3, 4, 5, 6];

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-lg">基本信息</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label htmlFor="title">作业标题 *</Label>
                        <Input id="title" {...register("title")} placeholder="请输入作业标题" />
                        {errors.title && <p className="text-sm text-destructive">{String(errors.title.message)}</p>}
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="topic">探究主题 *</Label>
                        <Input id="topic" {...register("topic")} placeholder="例如：气候变化与农业" />
                        {errors.topic && <p className="text-sm text-destructive">{String(errors.topic.message)}</p>}
                    </div>
                </div>

                <div className="space-y-2">
                    <Label htmlFor="description">作业描述</Label>
                    <Textarea id="description" {...register("description")} rows={3} />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-2">
                        <Label>学段</Label>
                        <Controller
                            control={control}
                            name="school_stage"
                            render={({ field }) => (
                                <Select onValueChange={field.onChange} defaultValue={field.value} value={field.value}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="选择学段" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="primary">小学</SelectItem>
                                        <SelectItem value="middle">初中</SelectItem>
                                    </SelectContent>
                                </Select>
                            )}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label>年级</Label>
                        <Controller
                            control={control}
                            name="grade"
                            render={({ field }) => (
                                <Select onValueChange={(val: string) => field.onChange(Number(val))} value={String(field.value)}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="选择年级" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {grades.map(g => (
                                            <SelectItem key={g} value={String(g)}>
                                                {schoolStage === 'middle' ? `初中${g - 6}` : `小学${g}`}年级
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            )}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label>时长 (周)</Label>
                        <Input type="number" {...register("duration_weeks")} min={1} />
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
