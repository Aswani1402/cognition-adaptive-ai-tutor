import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import BottomNav from './BottomNav';
import AuthGate from './AuthGate';

export default function MainLayout() {
  return (
    <AuthGate>
      <div className="flex h-screen bg-[#F8FAF5] dark:bg-[#0b1220] text-slate-900 dark:text-slate-50 overflow-hidden font-sans">
        <Sidebar />
        <div className="min-w-0 flex-1 flex flex-col md:pl-64">
          <Topbar />
          <main className="min-w-0 flex-1 overflow-y-auto w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-24 md:pb-6 relative">
            <Outlet />
          </main>
          <BottomNav />
        </div>
      </div>
    </AuthGate>
  );
}
