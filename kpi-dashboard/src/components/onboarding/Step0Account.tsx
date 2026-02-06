/**
 * Step 0: Account Creation & Billing
 */

import React, { useState, useEffect } from 'react';
import { CreditCard, Check, Info } from 'lucide-react';
import { AccountInfo } from './OnboardingWizard.types';
import { SUBSCRIPTION_PLANS } from './OnboardingWizard.config';
import { calculatePasswordStrength, isValidEmail } from './OnboardingWizard.utils';

interface Step0AccountProps {
  data: AccountInfo;
  onChange: (data: AccountInfo) => void;
}

export const Step0Account: React.FC<Step0AccountProps> = ({ data, onChange }) => {
  const [passwordStrength, setPasswordStrength] = useState(0);
  const [emailError, setEmailError] = useState('');

  useEffect(() => {
    const strength = calculatePasswordStrength(data.password);
    setPasswordStrength(strength);
  }, [data.password]);

  const handleEmailChange = (email: string) => {
    onChange({ ...data, email });
    if (email && !isValidEmail(email)) {
      setEmailError('Please enter a valid email address');
    } else {
      setEmailError('');
    }
  };

  return (
    <div className="space-y-6">
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start gap-2">
          <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">Welcome to CustomerSuccessAI!</p>
            <p>Create your account to get started. You can change your plan later.</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Left Column: Account Details */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Email Address *</label>
            <input
              type="email"
              value={data.email}
              onChange={(e) => handleEmailChange(e.target.value)}
              className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                emailError ? 'border-red-500' : ''
              }`}
              placeholder="you@company.com"
            />
            {emailError && (
              <p className="text-xs text-red-600 mt-1">{emailError}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Password *</label>
            <input
              type="password"
              value={data.password}
              onChange={(e) => onChange({ ...data, password: e.target.value })}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Minimum 8 characters"
            />
            {data.password && (
              <div className="mt-2">
                <div className="flex gap-1 h-1">
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className={`flex-1 rounded ${
                        i <= passwordStrength
                          ? passwordStrength <= 2
                            ? 'bg-red-500'
                            : passwordStrength === 3
                            ? 'bg-yellow-500'
                            : 'bg-green-500'
                          : 'bg-gray-200'
                      }`}
                    />
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {passwordStrength <= 2 && 'Weak password'}
                  {passwordStrength === 3 && 'Medium password'}
                  {passwordStrength === 4 && 'Strong password'}
                </p>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Company Domain *</label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={data.company_domain}
                onChange={(e) => onChange({ ...data, company_domain: e.target.value })}
                className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="company"
              />
              <span className="text-gray-500">.customersuccess.ai</span>
            </div>
            <p className="text-xs text-gray-500 mt-1">Your dashboard URL: {data.company_domain || 'company'}.customersuccess.ai</p>
          </div>
        </div>

        {/* Right Column: Subscription Plans */}
        <div className="space-y-4">
          <label className="block text-sm font-medium mb-2">Subscription Plan *</label>
          <div className="space-y-3">
            {SUBSCRIPTION_PLANS.map((plan) => (
              <div
                key={plan.id}
                onClick={() => onChange({ ...data, subscription_plan: plan.id })}
                className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                  data.subscription_plan === plan.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <h4 className="font-medium">{plan.name}</h4>
                    <p className="text-2xl font-bold mt-1">
                      ${plan.price}
                      <span className="text-sm font-normal text-gray-500">/month</span>
                    </p>
                  </div>
                  {data.subscription_plan === plan.id && (
                    <Check className="w-6 h-6 text-blue-600" />
                  )}
                </div>
                <ul className="text-xs text-gray-600 space-y-1">
                  {plan.features.map((feature, i) => (
                    <li key={i} className="flex items-center gap-1">
                      <Check className="w-3 h-3" />
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {data.subscription_plan !== 'free' && (
            <div className="mt-4">
              <label className="block text-sm font-medium mb-2">Payment Method *</label>
              <select
                value={data.payment_method || 'card'}
                onChange={(e) => onChange({ ...data, payment_method: e.target.value as any })}
                className="w-full px-4 py-2 border rounded-lg"
              >
                <option value="card">Credit Card</option>
                {data.subscription_plan === 'enterprise' && (
                  <option value="invoice">Invoice (Enterprise only)</option>
                )}
              </select>
              {data.payment_method === 'card' && (
                <div className="mt-3 p-3 bg-gray-50 rounded-lg text-sm text-gray-600 flex items-center gap-2">
                  <CreditCard className="w-4 h-4" />
                  <span>Payment will be processed after setup completion</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
