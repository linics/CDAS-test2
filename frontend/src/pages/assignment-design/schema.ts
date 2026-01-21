import { z } from "zod";

export const assignmentFormSchema = z.object({
    title: z.string().min(2, "标题至少需要2个字符"),
    topic: z.string().min(2, "主题至少需要2个字符"),
    description: z.string().optional(),
    school_stage: z.enum(["primary", "middle"]),
    grade: z.coerce.number().min(1).max(9),
    main_subject_id: z.coerce.number().min(1, "请选择主导学科"),
    related_subject_ids: z.array(z.coerce.number()).default([]),
    assignment_type: z.enum(["practical", "inquiry", "project"]),
    inquiry_depth: z.enum(["basic", "intermediate", "deep"]),
    submission_mode: z.enum(["phased", "once"]),
    duration_weeks: z.coerce.number().min(1),
    practical_subtype: z.enum(["visit", "simulation", "observation"]).optional(),
    inquiry_subtype: z.enum(["literature", "survey", "experiment"]).optional(),

    // AI Preview Data (Hidden or Managed separately)
    objectives_json: z.any().optional(),
    phases_json: z.any().optional(),
    rubric_json: z.any().optional(),
});

export type AssignmentFormValues = z.infer<typeof assignmentFormSchema>;
