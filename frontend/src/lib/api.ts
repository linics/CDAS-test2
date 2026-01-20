// API v2 客户端 - 用于新版API
import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

// 创建 API 客户端实例
export const apiClient = axios.create({
    baseURL: API_BASE_URL || undefined,
    headers: {
        "Content-Type": "application/json",
    },
});

// 获取 Token
export const getToken = (): string | null => {
    return localStorage.getItem("cdas_token");
};

// 设置 Token
export const setToken = (token: string): void => {
    localStorage.setItem("cdas_token", token);
};

// 清除 Token
export const clearToken = (): void => {
    localStorage.removeItem("cdas_token");
};

// 请求拦截器 - 自动添加 Token
apiClient.interceptors.request.use(
    (config) => {
        const token = getToken();
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// 响应拦截器 - 处理错误
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Token 过期或无效，清除并跳转登录
            clearToken();
            window.location.href = "/login";
        }
        return Promise.reject(error);
    }
);

// ============ API v2 接口 ============

// 认证 API
export const authApi = {
    register: (data: {
        username: string;
        password: string;
        role: "teacher" | "student";
        name: string;
        grade?: number;
        class_name?: string;
    }) => apiClient.post("/api/v2/auth/register", data),

    login: (username: string, password: string) => {
        const params = new URLSearchParams();
        params.append('username', username);
        params.append('password', password);
        return apiClient.post("/api/v2/auth/login", params, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });
    },

    getMe: () => apiClient.get("/api/v2/auth/me"),
};

// 学科 API
export const subjectsApi = {
    list: (stage?: string, category?: string) =>
        apiClient.get("/api/v2/subjects/", { params: { stage, category } }),

    getById: (id: number) => apiClient.get(`/api/v2/subjects/${id}`),

    init: () => apiClient.post("/api/v2/subjects/init"),

    getCategories: () => apiClient.get("/api/v2/subjects/categories/list"),
};

// 作业 API
export const assignmentsApi = {
    create: (data: AssignmentCreate) =>
        apiClient.post("/api/v2/assignments/", data),
    preview: (data: AssignmentCreate) =>
        apiClient.post("/api/v2/assignments/preview", data),

    list: (page = 1, pageSize = 20, publishedOnly = false) =>
        apiClient.get("/api/v2/assignments/", {
            params: { page, page_size: pageSize, published_only: publishedOnly }
        }),

    getById: (id: number) => apiClient.get(`/api/v2/assignments/${id}`),

    update: (id: number, data: Partial<AssignmentCreate>) =>
        apiClient.put(`/api/v2/assignments/${id}`, data),

    delete: (id: number) => apiClient.delete(`/api/v2/assignments/${id}`),

    publish: (id: number) => apiClient.post(`/api/v2/assignments/${id}/publish`),

    generateSteps: (id: number) =>
        apiClient.post(`/api/v2/assignments/${id}/generate-steps`),

    // 小组
    createGroup: (assignmentId: number, data: { name: string; members_json: any[] }) =>
        apiClient.post(`/api/v2/assignments/${assignmentId}/groups`, data),

    listGroups: (assignmentId: number) =>
        apiClient.get(`/api/v2/assignments/${assignmentId}/groups`),
};

// 提交 API
export const submissionsApi = {
    create: (data: SubmissionCreate) =>
        apiClient.post("/api/v2/submissions/", data),

    listMy: (assignmentId?: number) =>
        apiClient.get("/api/v2/submissions/my", {
            params: assignmentId ? { assignment_id: assignmentId } : {}
        }),

    getById: (id: number) => apiClient.get(`/api/v2/submissions/${id}`),

    update: (id: number, data: Partial<SubmissionCreate>) =>
        apiClient.put(`/api/v2/submissions/${id}`, data),

    submit: (id: number) => apiClient.post(`/api/v2/submissions/${id}/submit`),

    delete: (id: number) => apiClient.delete(`/api/v2/submissions/${id}`),

    listByAssignment: (assignmentId: number, phaseIndex?: number) =>
        apiClient.get(`/api/v2/submissions/assignment/${assignmentId}`, {
            params: phaseIndex !== undefined ? { phase_index: phaseIndex } : {}
        }),
};

// 评价 API
export const evaluationsApi = {
    createTeacher: (data: TeacherEvaluationCreate) =>
        apiClient.post("/api/v2/evaluations/teacher", data),

    createSelf: (data: SelfEvaluationCreate) =>
        apiClient.post("/api/v2/evaluations/self", data),

    createPeer: (data: PeerEvaluationCreate) =>
        apiClient.post("/api/v2/evaluations/peer", data),

    listBySubmission: (submissionId: number) =>
        apiClient.get(`/api/v2/evaluations/submission/${submissionId}`),

    aiAssist: (submissionId: number) =>
        apiClient.post("/api/v2/evaluations/ai-assist", null, {
            params: { submission_id: submissionId }
        }),

    listMyReceived: () => apiClient.get("/api/v2/evaluations/my-received"),
};

// ============ 类型定义 ============

export interface AssignmentCreate {
    title: string;
    topic: string;
    description?: string;
    school_stage: "primary" | "middle";
    grade: number;
    main_subject_id: number;
    related_subject_ids?: number[];
    assignment_type: "practical" | "inquiry" | "project";
    practical_subtype?: "visit" | "simulation" | "observation";
    inquiry_subtype?: "literature" | "survey" | "experiment";
    inquiry_depth?: "basic" | "intermediate" | "deep";
    submission_mode?: "phased" | "once" | "mixed";
    duration_weeks?: number;
    deadline?: string;
    objectives_json?: Record<string, any>;
    phases_json?: Phase[];
    rubric_json?: Record<string, any>;
}

export interface SubmissionCreate {
    assignment_id: number;
    phase_index: number;
    step_index?: number;
    group_id?: number;
    content_json?: Record<string, any>;
    attachments_json?: { filename: string; url: string; type: string }[];
    checkpoints_json?: Record<string, boolean>;
}

export interface TeacherEvaluationCreate {
    submission_id: number;
    score_numeric: number;
    score_level?: "A" | "B" | "C" | "D";
    dimension_scores_json?: Record<string, number>;
    feedback: string;
}

export interface SelfEvaluationCreate {
    submission_id: number;
    completion: number;
    effort: number;
    difficulties?: string;
    gains?: string;
    improvement?: string;
}

export interface PeerEvaluationCreate {
    submission_id: number;
    quality: number;
    clarity: number;
    highlights?: string;
    suggestions?: string;
}

export interface User {
    id: number;
    username: string;
    role: "teacher" | "student";
    name: string;
    grade?: number;
    class_name?: string;
}

export interface Subject {
    id: number;
    code: string;
    name: string;
    category: string;
    primary_available: boolean;
    middle_available: boolean;
    core_competencies: { dimension: string; description: string }[];
}

export interface Assignment {
    id: number;
    title: string;
    topic: string;
    description?: string;
    school_stage: string;
    grade: number;
    main_subject_id: number;
    related_subject_ids: number[];
    assignment_type: string;
    inquiry_depth: string;
    submission_mode: string;
    phases_json: Phase[];
    rubric_json: Record<string, any>;
    is_published: boolean;
    created_at: string;
}

export interface Phase {
    name: string;
    order: number;
    steps: Step[];
}

export interface Step {
    name: string;
    description: string;
    checkpoints: { content: string; evidence_type: string }[];
}
