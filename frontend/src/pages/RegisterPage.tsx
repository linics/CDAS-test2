// 注册页面

import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import "./LoginPage.css"; // 复用登录页样式

const RegisterPage: React.FC = () => {
    const [formData, setFormData] = useState({
        username: "",
        password: "",
        confirmPassword: "",
        name: "",
        role: "student" as "teacher" | "student",
        grade: 7,
        class_name: "",
    });
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const { register } = useAuth();
    const navigate = useNavigate();

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: name === "grade" ? parseInt(value) : value
        }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (formData.password !== formData.confirmPassword) {
            setError("两次输入的密码不一致");
            return;
        }

        if (formData.password.length < 6) {
            setError("密码长度至少6位");
            return;
        }

        setIsLoading(true);

        try {
            await register({
                username: formData.username,
                password: formData.password,
                name: formData.name,
                role: formData.role,
                grade: formData.role === "student" ? formData.grade : undefined,
                class_name: formData.role === "student" ? formData.class_name : undefined,
            });
            navigate("/");
        } catch (err: any) {
            setError(err.response?.data?.detail || "注册失败");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="login-page">
            <div className="login-container" style={{ maxWidth: "480px" }}>
                <div className="login-header">
                    <h1>跨学科作业系统</h1>
                    <p>创建您的账号</p>
                </div>

                <form className="login-form" onSubmit={handleSubmit}>
                    <h2>用户注册</h2>

                    {error && <div className="error-message">{error}</div>}

                    <div className="form-group">
                        <label htmlFor="role">我是</label>
                        <select
                            id="role"
                            name="role"
                            value={formData.role}
                            onChange={handleChange}
                            style={{
                                width: "100%",
                                padding: "0.75rem 1rem",
                                border: "1px solid #ddd",
                                borderRadius: "8px",
                                fontSize: "1rem",
                            }}
                        >
                            <option value="student">学生</option>
                            <option value="teacher">教师</option>
                        </select>
                    </div>

                    <div className="form-group">
                        <label htmlFor="name">姓名</label>
                        <input
                            type="text"
                            id="name"
                            name="name"
                            value={formData.name}
                            onChange={handleChange}
                            placeholder="请输入真实姓名"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="username">用户名</label>
                        <input
                            type="text"
                            id="username"
                            name="username"
                            value={formData.username}
                            onChange={handleChange}
                            placeholder="用于登录的用户名"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">密码</label>
                        <input
                            type="password"
                            id="password"
                            name="password"
                            value={formData.password}
                            onChange={handleChange}
                            placeholder="至少6位"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="confirmPassword">确认密码</label>
                        <input
                            type="password"
                            id="confirmPassword"
                            name="confirmPassword"
                            value={formData.confirmPassword}
                            onChange={handleChange}
                            placeholder="再次输入密码"
                            required
                        />
                    </div>

                    {formData.role === "student" && (
                        <>
                            <div className="form-group">
                                <label htmlFor="grade">年级</label>
                                <select
                                    id="grade"
                                    name="grade"
                                    value={formData.grade}
                                    onChange={handleChange}
                                    style={{
                                        width: "100%",
                                        padding: "0.75rem 1rem",
                                        border: "1px solid #ddd",
                                        borderRadius: "8px",
                                        fontSize: "1rem",
                                    }}
                                >
                                    {[1, 2, 3, 4, 5, 6].map(g => (
                                        <option key={g} value={g}>小学{g}年级</option>
                                    ))}
                                    {[7, 8, 9].map(g => (
                                        <option key={g} value={g}>初中{g - 6}年级</option>
                                    ))}
                                </select>
                            </div>

                            <div className="form-group">
                                <label htmlFor="class_name">班级</label>
                                <input
                                    type="text"
                                    id="class_name"
                                    name="class_name"
                                    value={formData.class_name}
                                    onChange={handleChange}
                                    placeholder="如：1班"
                                />
                            </div>
                        </>
                    )}

                    <button
                        type="submit"
                        className="login-button"
                        disabled={isLoading}
                    >
                        {isLoading ? "注册中..." : "注册"}
                    </button>
                </form>

                <div className="login-footer">
                    <p>
                        已有账号？<Link to="/login">立即登录</Link>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default RegisterPage;
