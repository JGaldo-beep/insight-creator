"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Menu,
  MessageSquare,
  Sparkles,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessageSquare },
];

function Brand() {
  return (
    <div className="flex items-center gap-2">
      <div className="flex size-8 items-center justify-center rounded-md bg-foreground text-background">
        <Sparkles className="size-4" />
      </div>
      <div className="flex flex-col leading-tight">
        <span className="text-sm font-semibold tracking-tight text-sidebar-foreground">
          Insight Extractor
        </span>
        <span className="text-[11px] text-muted-foreground">Marketing AI</span>
      </div>
    </div>
  );
}

export function SidebarNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  // Cierra el drawer al navegar
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // Cierra con Escape
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  // Bloquea el scroll del body cuando el drawer está abierto
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  const navLinks = (
    <nav className="flex flex-col gap-1">
      {items.map(({ href, label, icon: Icon }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            onClick={() => setOpen(false)}
            className={cn(
              "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
              active
                ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
            )}
          >
            <Icon className="size-4" />
            {label}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <>
      {/* Top bar mobile (fija) */}
      <div className="fixed inset-x-0 top-0 z-30 flex h-14 items-center justify-between border-b border-sidebar-border bg-sidebar/90 px-3 backdrop-blur md:hidden">
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Abrir menú"
          aria-expanded={open}
          aria-controls="mobile-sidebar"
          className="inline-flex size-10 items-center justify-center rounded-md text-sidebar-foreground hover:bg-sidebar-accent/60"
        >
          <Menu className="size-5" />
        </button>
        <div className="pr-2">
          <Brand />
        </div>
      </div>

      {/* Backdrop mobile */}
      <button
        type="button"
        aria-label="Cerrar menú"
        tabIndex={open ? 0 : -1}
        onClick={() => setOpen(false)}
        className={cn(
          "fixed inset-0 z-40 bg-black/30 backdrop-blur-sm transition-opacity md:hidden",
          open
            ? "opacity-100 pointer-events-auto"
            : "opacity-0 pointer-events-none",
        )}
      />

      {/* Sidebar — fija en desktop, drawer en mobile */}
      <aside
        id="mobile-sidebar"
        aria-hidden={!open}
        className={cn(
          "flex w-64 shrink-0 flex-col gap-6 border-r border-sidebar-border bg-sidebar px-4 py-6",
          // Mobile: fixed drawer
          "fixed inset-y-0 left-0 z-50 transition-transform duration-200 ease-out",
          open ? "translate-x-0" : "-translate-x-full",
          // Desktop: static, siempre visible
          "md:static md:z-auto md:w-60 md:translate-x-0",
        )}
      >
        <div className="flex items-center justify-between">
          <Brand />
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Cerrar menú"
            className="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-sidebar-accent/60 md:hidden"
          >
            <X className="size-4" />
          </button>
        </div>
        {navLinks}
      </aside>
    </>
  );
}
