import Link from "next/link";
import { Home, Users, FileText, LayoutDashboard } from "lucide-react";

export function Navigation() {
  return (
    <nav className="bg-card border-b">
      <div className="max-w-7xl mx-auto px-8">
        <div className="flex items-center gap-8 h-16">
          <Link href="/" className="font-bold text-xl">
            Outreach
          </Link>
          <div className="flex gap-6">
            <Link
              href="/"
              className="flex items-center gap-2 text-sm hover:text-primary"
            >
              <LayoutDashboard className="h-4 w-4" />
              Overview
            </Link>
            <Link
              href="/accounts"
              className="flex items-center gap-2 text-sm hover:text-primary"
            >
              <Users className="h-4 w-4" />
              Accounts
            </Link>
            <Link
              href="/logs"
              className="flex items-center gap-2 text-sm hover:text-primary"
            >
              <FileText className="h-4 w-4" />
              Logs
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}