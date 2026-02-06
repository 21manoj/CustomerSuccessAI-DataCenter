/**
 * Step 1: Vertical Selection & Business Context
 */

import React from 'react';
import { Check, Cloud, Server } from 'lucide-react';
import { BusinessContext } from './OnboardingWizard.types';
import { INDUSTRIES, SEGMENTS, CONTRACT_MODELS, CSM_MODELS } from './OnboardingWizard.config';

interface Step1BusinessProps {
  data: BusinessContext;
  onChange: (data: BusinessContext) => void;
}

export const Step1Business: React.FC<Step1BusinessProps> = ({ data, onChange }) => {
  return (
    <div className="space-y-6">
      {/* Vertical Selection */}
      <div>
        <label className="block text-sm font-medium mb-3">Select Your Vertical *</label>
        <p className="text-sm text-gray-600 mb-4">
          Choose the vertical that best matches your customer success model. This determines your KPI pillars and event types.
        </p>
        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={() => onChange({ ...data, vertical: 'saas' })}
            className={`p-6 border-2 rounded-lg text-left transition-all ${
              data.vertical === 'saas'
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <Cloud className={`w-8 h-8 ${data.vertical === 'saas' ? 'text-blue-600' : 'text-gray-400'}`} />
              {data.vertical === 'saas' && <Check className="w-6 h-6 text-blue-600" />}
            </div>
            <h3 className="font-semibold text-lg mb-1">SaaS</h3>
            <p className="text-sm text-gray-600">
              Product usage, feature adoption, NPS, support tickets, engagement metrics
            </p>
            <p className="text-xs text-gray-500 mt-2">
              Best for: Software companies, subscription services, cloud platforms
            </p>
          </button>

          <button
            onClick={() => onChange({ ...data, vertical: 'datacenter' })}
            className={`p-6 border-2 rounded-lg text-left transition-all ${
              data.vertical === 'datacenter'
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <Server className={`w-8 h-8 ${data.vertical === 'datacenter' ? 'text-blue-600' : 'text-gray-400'}`} />
              {data.vertical === 'datacenter' && <Check className="w-6 h-6 text-blue-600" />}
            </div>
            <h3 className="font-semibold text-lg mb-1">Data Center</h3>
            <p className="text-sm text-gray-600">
              Deployment, stability, performance, uptime, incident management
            </p>
            <p className="text-xs text-gray-500 mt-2">
              Best for: Infrastructure providers, hosting services, data center operations
            </p>
          </button>
        </div>
      </div>

      {data.vertical && (
        <div className="border-t pt-6 space-y-6">
          <div>
            <label className="block text-sm font-medium mb-2">Company Name *</label>
            <input
              type="text"
              value={data.company_name}
              onChange={(e) => onChange({ ...data, company_name: e.target.value })}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Enter your company name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Industry *</label>
            <div className="grid grid-cols-4 gap-2">
              {INDUSTRIES.map((ind) => (
                <button
                  key={ind}
                  onClick={() => onChange({ ...data, industry: ind })}
                  className={`px-4 py-2 rounded-lg border text-sm ${
                    data.industry === ind
                      ? 'bg-blue-50 border-blue-500 text-blue-700'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  {ind}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Customer Segments *</label>
            <div className="grid grid-cols-4 gap-2">
              {SEGMENTS.map((seg) => (
                <button
                  key={seg}
                  onClick={() => {
                    const newSegments = data.segments.includes(seg)
                      ? data.segments.filter((s) => s !== seg)
                      : [...data.segments, seg];
                    onChange({ ...data, segments: newSegments });
                  }}
                  className={`px-4 py-2 rounded-lg border text-sm flex items-center justify-center gap-2 ${
                    data.segments.includes(seg)
                      ? 'bg-blue-50 border-blue-500 text-blue-700'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  {data.segments.includes(seg) && <Check className="w-4 h-4" />}
                  {seg}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Average Deal Size: ${data.avg_deal_size.toLocaleString()}
            </label>
            <input
              type="range"
              min={10000}
              max={1000000}
              step={10000}
              value={data.avg_deal_size}
              onChange={(e) => onChange({ ...data, avg_deal_size: Number(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>$10K</span>
              <span>$500K</span>
              <span>$1M+</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Contract Model</label>
              <select
                value={data.contract_model}
                onChange={(e) => onChange({ ...data, contract_model: e.target.value })}
                className="w-full px-4 py-2 border rounded-lg"
              >
                {CONTRACT_MODELS.map((model) => (
                  <option key={model} value={model.toLowerCase().replace('-', '_')}>
                    {model}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">CSM Model</label>
              <select
                value={data.csm_model}
                onChange={(e) => onChange({ ...data, csm_model: e.target.value })}
                className="w-full px-4 py-2 border rounded-lg"
              >
                {CSM_MODELS.map((model) => (
                  <option key={model} value={model.toLowerCase().replace('-', '_')}>
                    {model}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
