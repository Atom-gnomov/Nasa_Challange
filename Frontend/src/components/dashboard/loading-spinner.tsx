
"use client";

import { Loader2 } from "lucide-react";

export default function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center text-center p-12 h-full">
      <div className="bg-white/20 backdrop-blur-sm p-8 rounded-2xl shadow-lg flex flex-col items-center gap-4">
        <Loader2 className="h-16 w-16 animate-spin text-white" />
        <h2 className="text-2xl font-bold font-headline mt-4 mb-2 text-white">
          Generating your forecast...
        </h2>
        <p className="text-gray-200 max-w-md">
          This may take up to a minute. Please wait.
        </p>
      </div>
    </div>
  );
}
