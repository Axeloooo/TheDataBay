import React from "react";
import Navbar from "@/components/navbar";

interface LayoutProps {
  children: React.ReactNode;
}

function Layout({ children }: LayoutProps) {
  return (
    <>
      <header className="sticky top-0 z-50 w-full border-b bg-background">
        <div className="container mx-auto flex h-16 items-center px-4">
          <Navbar></Navbar>
        </div>
      </header>
      <main className="flex-1 w-full">
        <div className="container mx-auto px-4 py-6">{children}</div>
      </main>
    </>
  );
}

export default Layout;
