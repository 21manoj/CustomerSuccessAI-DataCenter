import React, { useState, useRef } from 'react';
import { Eye } from 'lucide-react';

interface Account {
  account_id: number;
  account_name: string;
  revenue: number;
  industry: string;
  region: string;
  account_status: string;
  health_score: number;
  external_account_id?: string;
  profile_metadata?: {
    account_tier?: string;
    assigned_csm?: string;
    csm_manager?: string;
    products_used?: string;
    engagement?: {
      lifecycle_stage?: string;
      onboarding_status?: string;
    };
    champions?: Array<{
      primary_champion_name?: string;
      champion_title?: string;
      champion_email?: string;
      champion_status?: string;
    }>;
  };
  products_used?: string[];
  primary_champion_name?: string;
}

interface AccountHealthHeatmapProps {
  accounts: Account[];
  onAccountClick?: (account: Account | null) => void;
  selectedAccountId?: number | null;
}

const AccountHealthHeatmap: React.FC<AccountHealthHeatmapProps> = ({ accounts, onAccountClick, selectedAccountId }) => {

  // Get health status and color
  const getHealthStatus = (score: number) => {
    if (score >= 80) return { status: 'Healthy', color: 'green' };
    if (score >= 70) return { status: 'At Risk', color: 'yellow' };
    return { status: 'Critical', color: 'red' };
  };

  // Get cell color based on health score (Finviz-style intensity)
  const getCellColor = (healthScore: number): string => {
    if (healthScore >= 80) {
      // Green gradient: darker = better (closer to 100)
      if (healthScore >= 95) return 'bg-green-700';
      if (healthScore >= 90) return 'bg-green-600';
      return 'bg-green-500';
    }
    if (healthScore >= 70) {
      // Yellow gradient: darker = worse (closer to 70)
      if (healthScore <= 72) return 'bg-yellow-600';
      return 'bg-yellow-500';
    }
    // Red gradient: darker = worse (closer to 0)
    if (healthScore <= 50) return 'bg-red-700';
    if (healthScore <= 60) return 'bg-red-600';
    return 'bg-red-500';
  };

  // Get cell size based on revenue (logarithmic scale)
  const getCellSize = (revenue: number): { width: string; height: string } => {
    if (revenue === 0) return { width: '80px', height: '80px' };
    const logRevenue = Math.log10(revenue);
    const size = Math.min(140, Math.max(80, logRevenue * 25));
    return { width: `${size}px`, height: `${size}px` };
  };

  // Handle cell click
  const handleCellClick = (account: Account) => {
    if (selectedAccountId === account.account_id) {
      // Deselect if clicking the same account
      onAccountClick?.(null);
    } else {
      // Select the clicked account
      onAccountClick?.(account);
    }
  };

  // Get products used text
  const getProductsUsed = (account: Account): string => {
    const profileProducts = account.profile_metadata?.products_used;
    if (profileProducts && profileProducts.trim()) {
      return profileProducts;
    }
    if (account.products_used && account.products_used.length > 0) {
      return account.products_used.join(', ');
    }
    return 'N/A';
  };

  // Get champion name
  const getChampionName = (account: Account): string => {
    return account.primary_champion_name || 
           account.profile_metadata?.champions?.[0]?.primary_champion_name || 
           'N/A';
  };

  if (accounts.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>No accounts found. Upload data to get started.</p>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Heatmap Grid */}
      <div className="grid grid-cols-[repeat(auto-fill,minmax(100px,1fr))] gap-3 p-4">
        {accounts.map((account) => {
          const healthStatus = getHealthStatus(account.health_score);
          const cellColor = getCellColor(account.health_score);
          const cellSize = getCellSize(account.revenue);
          
          return (
            <div
              key={account.account_id}
              className={`${cellColor} rounded-lg cursor-pointer transition-all duration-200 hover:scale-110 hover:shadow-lg hover:z-10 relative flex items-center justify-center group border-2 border-black ${
                selectedAccountId === account.account_id ? 'ring-4 ring-blue-500 ring-offset-2' : ''
              }`}
              style={cellSize}
              onClick={() => handleCellClick(account)}
            >
              {/* Account Name (truncated) */}
              <div className="text-white text-xs font-semibold px-2 text-center truncate w-full">
                {account.account_name.length > 15 
                  ? account.account_name.substring(0, 15) + '...'
                  : account.account_name}
              </div>
              
              {/* Health Score Badge */}
              <div className="absolute bottom-1 right-1 bg-black bg-opacity-50 rounded px-1 text-xs text-white">
                {account.health_score?.toFixed(0) || 'N/A'}
              </div>
            </div>
          );
        })}
      </div>


      {/* CSS Animation */}
      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-5px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
};

export default AccountHealthHeatmap;

