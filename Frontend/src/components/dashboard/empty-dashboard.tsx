
"use client";

import { Plus } from "lucide-react";

export default function EmptyDashboard({ onAddActivity }: { onAddActivity: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center text-center p-12 h-full">
      <div className="bg-white/20 backdrop-blur-sm p-8 rounded-2xl shadow-lg flex flex-col items-center">
        <button 
          onClick={onAddActivity} 
          className="p-4 bg-gray-200/80 rounded-full mb-4 transition-all duration-300 ease-in-out hover:bg-gray-300 hover:scale-105"
          aria-label="Add new activity"
        >
            <div className="w-32 h-32 bg-white flex items-center justify-center rounded-full text-gray-400" >
              <Plus className="w-20 h-20" />
            </div>
        </button>
        <h2 className="text-2xl font-bold font-headline mt-4 mb-2 text-white">Your Dashboard is Empty</h2>
        <p className="text-gray-200 max-w-md">
          Welcome to Stratoforce! Get started by clicking the "+" button to add your first planned activity and see AI-powered insights.
        </p>
      </div>
    </div>
  );
}
