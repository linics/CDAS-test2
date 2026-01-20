import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Outlet, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import KnowledgeBasePage from './pages/KnowledgeBasePage';
import AssignmentPage from './pages/AssignmentPage';
import GroupsPage from './pages/GroupsPage';
import SubmissionPage from './pages/SubmissionPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import AssignmentsPage from './pages/AssignmentsPage';
import AssignmentDesignPage from './pages/AssignmentDesignPage';
import AssignmentSubmissionsPage from './pages/AssignmentSubmissionsPage';
import GradingPage from './pages/GradingPage';
import MyAssignmentsPage from './pages/MyAssignmentsPage';
import StudentSubmissionPage from './pages/StudentSubmissionPage';
import StudentEvaluationPage from './pages/StudentEvaluationPage';
import EvaluationsPage from './pages/EvaluationsPage';

const queryClient = new QueryClient();

// 路由保护组件
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen flex flex-col archive-app">
      <nav className="archive-nav px-6 py-4 flex items-center justify-between sticky top-0 z-10 shadow-sm">
        <div className="flex items-center gap-8">
          <Link to="/" className="archive-brand font-bold text-2xl">CDAS</Link>
          <div className="flex items-center gap-4 text-sm font-medium">
            {user?.role === 'teacher' ? (
              <>
                <Link to="/inventory" className="text-gray-700 hover:text-black transition">资料库</Link>
                <Link to="/assignments" className="text-gray-700 hover:text-black transition">作业管理</Link>
                <Link to="/evaluations" className="text-gray-700 hover:text-black transition">评价批改</Link>
              </>
            ) : (
              <>
                <Link to="/my-assignments" className="text-gray-700 hover:text-black transition">我的作业</Link>
                <Link to="/my-submissions" className="text-gray-700 hover:text-black transition">我的提交</Link>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-700">
            {user?.name} ({user?.role === 'teacher' ? '教师' : '学生'})
          </span>
          <button
            onClick={logout}
            className="text-sm text-gray-600 hover:text-red-600 transition"
          >
            退出
          </button>
        </div>
      </nav>
      <main className="container mx-auto py-10 px-4 flex-1">
        <Outlet />
      </main>
    </div>
  )
}

function Dashboard() {
  const { user } = useAuth();

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div className="space-y-2">
        <h1 className="text-4xl font-extrabold tracking-tight text-gray-900">
          欢迎，{user?.name}
        </h1>
        <p className="text-lg text-gray-500">跨学科作业系统 - CDAS</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {user?.role === 'teacher' ? (
          <>
            <Link to="/inventory" className="group block p-6 bg-white border rounded-xl hover:shadow-lg transition-all hover:-translate-y-1">
              <div className="h-12 w-12 bg-blue-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-blue-100 transition">
                <span className="text-2xl">📚</span>
              </div>
              <h2 className="text-xl font-semibold mb-2">资料库管理</h2>
              <p className="text-gray-500">上传课程资料，生成作业配置。</p>
            </Link>

            <Link to="/assignments" className="group block p-6 bg-white border rounded-xl hover:shadow-lg transition-all hover:-translate-y-1">
              <div className="h-12 w-12 bg-green-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-green-100 transition">
                <span className="text-2xl">📝</span>
              </div>
              <h2 className="text-xl font-semibold mb-2">作业设计</h2>
              <p className="text-gray-500">创建跨学科作业，设计任务引导。</p>
            </Link>

            <Link to="/evaluations" className="group block p-6 bg-white border rounded-xl hover:shadow-lg transition-all hover:-translate-y-1">
              <div className="h-12 w-12 bg-purple-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-purple-100 transition">
                <span className="text-2xl">✅</span>
              </div>
              <h2 className="text-xl font-semibold mb-2">评价批改</h2>
              <p className="text-gray-500">批改学生提交，AI辅助评价。</p>
            </Link>
          </>
        ) : (
          <>
            <Link to="/my-assignments" className="group block p-6 bg-white border rounded-xl hover:shadow-lg transition-all hover:-translate-y-1">
              <div className="h-12 w-12 bg-blue-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-blue-100 transition">
                <span className="text-2xl">📋</span>
              </div>
              <h2 className="text-xl font-semibold mb-2">我的作业</h2>
              <p className="text-gray-500">查看分配的作业，了解任务要求。</p>
            </Link>

            <Link to="/my-submissions" className="group block p-6 bg-white border rounded-xl hover:shadow-lg transition-all hover:-translate-y-1">
              <div className="h-12 w-12 bg-green-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-green-100 transition">
                <span className="text-2xl">📤</span>
              </div>
              <h2 className="text-xl font-semibold mb-2">提交作业</h2>
              <p className="text-gray-500">按阶段提交作业，查看评价反馈。</p>
            </Link>
          </>
        )}
      </div>
    </div>
  )
}

function App() {
  useEffect(() => {
    document.body.classList.add('archive-ui');
    return () => {
      document.body.classList.remove('archive-ui');
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <Routes>
            {/* 公开路由 */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* 受保护路由 */}
            <Route element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }>
              <Route path="/" element={<Dashboard />} />
              <Route path="/inventory" element={<KnowledgeBasePage />} />
              <Route path="/assignments/:id" element={<AssignmentPage />} />
              <Route path="/groups" element={<GroupsPage />} />
              <Route path="/submissions" element={<SubmissionPage />} />

              <Route path="/assignments" element={<AssignmentsPage />} />
              <Route path="/assignments/new" element={<AssignmentDesignPage />} />
              <Route path="/assignments/:id/edit" element={<AssignmentDesignPage />} />
              <Route path="/assignments/:assignmentId/submissions" element={<AssignmentSubmissionsPage />} />
              <Route path="/grading/:submissionId" element={<GradingPage />} />

              {/* 教师评价页 */}
              <Route path="/evaluations" element={<EvaluationsPage />} />
              <Route path="/my-assignments" element={<MyAssignmentsPage />} />
              <Route path="/my-details/:id" element={<StudentSubmissionPage />} />
              <Route path="/evaluate/:submissionId" element={<StudentEvaluationPage />} />
              <Route path="/my-submissions" element={<Navigate to="/my-assignments" replace />} />
            </Route>
          </Routes>
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
