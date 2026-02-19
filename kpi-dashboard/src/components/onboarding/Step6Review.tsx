/**
 * Step 6: Review & Confirm
 */

import React from 'react';
import { Building2, BarChart2, Target, Database, Download, CheckCircle, CreditCard, Users } from 'lucide-react';
import { OnboardingData } from './OnboardingWizard.types';

interface Step6ReviewProps {
  data: OnboardingData;
}

export const Step6Review: React.FC<Step6ReviewProps> = ({ data }) => {
  const pillarWeights = data.pillars.map((p, i) => ({
    ...p,
    weight: i === 0 ? 30 : i <= 2 ? 20 : 15
  }));

  const handleDownloadConfig = () => {
    const config = {
      account: data.account,
      business: data.business,
      pillars: data.pillars,
      events: data.events,
      criteria: data.criteria,
      sources: data.sources.map(s => ({
        id: s.id,
        name: s.name,
        type: s.type,
        status: s.status
      })),
      team: data.team
    };
    
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `onboarding-config-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
        <div className="flex items-center gap-2 text-green-800">
          <CheckCircle className="w-5 h-5" />
          <span className="font-medium">Configuration Complete!</span>
        </div>
        <p className="text-sm text-green-700 mt-1">
          Review your settings below before completing setup. You can download this configuration for your records.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Account & Plan */}
        <div className="p-4 border rounded-lg">
          <h4 className="font-medium mb-3 flex items-center gap-2">
            <CreditCard className="w-4 h-4" />
            Account Details
          </h4>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Email</dt>
              <dd className="font-medium">{data.account.email}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Domain</dt>
              <dd>{data.account.company_domain}.customersuccess.ai</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Plan</dt>
              <dd className="font-medium capitalize">{data.account.subscription_plan}</dd>
            </div>
            {data.account.subscription_plan !== 'free' && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Payment</dt>
                <dd className="capitalize">{data.account.payment_method || 'Card'}</dd>
              </div>
            )}
          </dl>
        </div>

        {/* Business Profile */}
        <div className="p-4 border rounded-lg">
          <h4 className="font-medium mb-3 flex items-center gap-2">
            <Building2 className="w-4 h-4" />
            Business Profile
          </h4>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Company</dt>
              <dd className="font-medium">{data.business.company_name || 'Not set'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Vertical</dt>
              <dd className="capitalize font-medium">{data.business.vertical || 'Not selected'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Industry</dt>
              <dd>{data.business.industry || 'Not set'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Segments</dt>
              <dd>{data.business.segments.join(', ') || 'Not set'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Avg Deal</dt>
              <dd>${data.business.avg_deal_size.toLocaleString()}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">CSM Model</dt>
              <dd className="capitalize">{data.business.csm_model.replace('_', '-')}</dd>
            </div>
          </dl>
        </div>

        {/* Pillar Weights */}
        <div className="p-4 border rounded-lg">
          <h4 className="font-medium mb-3 flex items-center gap-2">
            <BarChart2 className="w-4 h-4" />
            Pillar Weights
          </h4>
          <div className="space-y-2">
            {pillarWeights.sort((a, b) => a.rank - b.rank).map((pillar) => (
              <div key={pillar.id} className="flex items-center justify-between text-sm">
                <span>#{pillar.rank} {pillar.label}</span>
                <span className="font-medium text-blue-600">{pillar.weight}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Thresholds */}
        <div className="p-4 border rounded-lg">
          <h4 className="font-medium mb-3 flex items-center gap-2">
            <Target className="w-4 h-4" />
            Thresholds
          </h4>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Healthy</dt>
              <dd className="text-green-600 font-medium">≥{data.criteria.healthy_min}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">At-Risk</dt>
              <dd className="text-yellow-600 font-medium">{data.criteria.at_risk_min}-{data.criteria.healthy_min - 1}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Churn Alert</dt>
              <dd className="text-red-600 font-medium">≤{data.criteria.churn_alert}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Expansion Alert</dt>
              <dd className="text-green-600 font-medium">≥{data.criteria.expansion_alert}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Prediction</dt>
              <dd>{data.criteria.prediction_horizon} days</dd>
            </div>
          </dl>
        </div>

        {/* Data Sources & Onboarding Mode */}
        <div className="p-4 border rounded-lg">
          <h4 className="font-medium mb-3 flex items-center gap-2">
            <Database className="w-4 h-4" />
            Data Sources
          </h4>
          <div className="space-y-2 text-sm">
            {/* Onboarding Mode */}
            <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
              data.onboarding_mode === 'demo'
                ? 'bg-purple-50 border border-purple-200'
                : 'bg-blue-50 border border-blue-200'
            }`}>
              <span className="font-medium">
                {data.onboarding_mode === 'demo' ? 'Demo / Showcase Mode' : 'Custom CSV Upload Mode'}
              </span>
              {data.onboarding_mode === 'demo' && (
                <span className="text-xs text-purple-600">(10 accounts, 12 months, 4 journey patterns)</span>
              )}
            </div>

            {/* Uploaded files (custom mode) */}
            {data.onboarding_mode === 'custom' && (
              <>
                {data.sources.filter((s) => s.status !== 'pending' && s.status !== 'skipped').map((source) => (
                  <div key={source.id} className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span>{source.name}</span>
                    {source.rows && <span className="text-gray-500">({source.rows} rows)</span>}
                  </div>
                ))}
                {data.sources.filter((s) => s.status === 'pending' || s.status === 'skipped').length > 0 && (
                  <p className="text-gray-500 text-xs">
                    {data.sources.filter((s) => s.status === 'skipped').length} source(s) skipped
                  </p>
                )}
              </>
            )}
          </div>
        </div>

        {/* Team */}
        <div className="p-4 border rounded-lg">
          <h4 className="font-medium mb-3 flex items-center gap-2">
            <Users className="w-4 h-4" />
            Team Members
          </h4>
          <div className="space-y-2 text-sm">
            {data.team.length > 0 ? (
              <>
                {data.team.map((member, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span>{member.name}</span>
                    <span className="text-gray-500 capitalize text-xs">{member.role}</span>
                  </div>
                ))}
                <p className="text-gray-500 text-xs mt-2">
                  {data.team.filter(m => m.invited).length} invitation(s) sent
                </p>
              </>
            ) : (
              <p className="text-gray-500 text-xs">No team members added</p>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center gap-4 pt-4 border-t">
        <button
          onClick={handleDownloadConfig}
          className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded flex items-center gap-2 border"
        >
          <Download className="w-4 h-4" />
          Download Configuration
        </button>
      </div>
    </div>
  );
};
