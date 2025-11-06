"use client";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import { useMemo } from "react";

// Dynamically import both pages so they render only on client
const HostPage = dynamic(() => import("./ClientSessionPage"), { ssr: false });
const ViewerPage = dynamic(() => import("./ViewerSessionPage"), { ssr: false });

export default function SessionPage() {
  const searchParams = useSearchParams();
  const role = searchParams.get("role");  // "host" or "viewer"

  // pick which component to render
  const RenderedPage = useMemo(() => {
    if (role === "host") return HostPage;
    if (role === "viewer") return ViewerPage;
    return () => <div>Invalid or missing role parameter.</div>;
  }, [role]);

  return <RenderedPage />;
}


  // speech → WebSocket → DB (raw text) → Punctuation → Translation → DB (updated, multilingual, punctuated)