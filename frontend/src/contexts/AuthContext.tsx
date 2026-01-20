// 认证 Context - 管理用户登录状态

import React, { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";
import { authApi, getToken, setToken, clearToken } from "../lib/api";
import type { User } from "../lib/api";

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login: (username: string, password: string) => Promise<void>;
    logout: () => void;
    register: (data: RegisterData) => Promise<void>;
}

interface RegisterData {
    username: string;
    password: string;
    role: "teacher" | "student";
    name: string;
    grade?: number;
    class_name?: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // 初始化时检查Token
    useEffect(() => {
        const checkAuth = async () => {
            const token = getToken();
            if (token) {
                try {
                    const response = await authApi.getMe();
                    setUser(response.data);
                } catch {
                    clearToken();
                }
            }
            setIsLoading(false);
        };
        checkAuth();
    }, []);

    const login = async (username: string, password: string) => {
        const response = await authApi.login(username, password);
        setToken(response.data.access_token);
        const userResponse = await authApi.getMe();
        setUser(userResponse.data);
    };

    const logout = () => {
        clearToken();
        setUser(null);
    };

    const register = async (data: RegisterData) => {
        await authApi.register(data);
        // 注册后自动登录
        await login(data.username, data.password);
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                isLoading,
                isAuthenticated: !!user,
                login,
                logout,
                register,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = (): AuthContextType => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used within AuthProvider");
    }
    return context;
};

export default AuthContext;
