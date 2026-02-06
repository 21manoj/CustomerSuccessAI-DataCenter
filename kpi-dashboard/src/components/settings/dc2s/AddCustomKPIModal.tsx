import React, { useState } from 'react';
import { KPIDefinition } from '../../../hooks/useCustomerConfig';

interface AddCustomKPIModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (kpiCode: string, definition: KPIDefinition) => Promise<{ success: boolean; error?: string }>;
  defaultPillar?: string;
}

export const AddCustomKPIModal: React.FC<AddCustomKPIModalProps> = ({
  isOpen,
  onClose,
  onSave,
  defaultPillar = 'AI'
}) => {
  const [formData, setFormData] = useState({
    kpiCode: '',
    pillar: defaultPillar,
    name: '',
    description: '',
    unit: '%',
    target: '',
    operator: '>',
    rangeMin: '',
    rangeMax: ''
  });

  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [saving, setSaving] = useState(false);

  if (!isOpen) return null;

  const validate = () => {
    const newErrors: { [key: string]: string } = {};

    if (!formData.kpiCode.match(/^CUSTOM-[A-Z0-9-]+$/)) {
      newErrors.kpiCode = 'Must start with CUSTOM- and contain only uppercase letters, numbers, and hyphens';
    }

    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }

    if (!formData.target) {
      newErrors.target = 'Target value is required';
    }

    if (!formData.rangeMin || !formData.rangeMax) {
      newErrors.range = 'Both min and max range values are required';
    }

    if (formData.rangeMin && formData.rangeMax && parseFloat(formData.rangeMin) >= parseFloat(formData.rangeMax)) {
      newErrors.range = 'Min must be less than max';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    setSaving(true);

    const definition: KPIDefinition = {
      pillar: formData.pillar,
      name: formData.name,
      description: formData.description,
      unit: formData.unit,
      target: parseFloat(formData.target),
      operator: formData.operator as any,
      range: [parseFloat(formData.rangeMin), parseFloat(formData.rangeMax)]
    };

    const result = await onSave(formData.kpiCode, definition);

    setSaving(false);

    if (result.success) {
      onClose();
      // Reset form
      setFormData({
        kpiCode: '',
        pillar: defaultPillar,
        name: '',
        description: '',
        unit: '%',
        target: '',
        operator: '>',
        rangeMin: '',
        rangeMax: ''
      });
      setErrors({});
    } else {
      setErrors({ ...errors, submit: result.error || 'Failed to save' });
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h2 className="text-2xl font-bold mb-4">Add Custom KPI</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* KPI Code */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                KPI Code *
              </label>
              <input
                type="text"
                value={formData.kpiCode}
                onChange={(e) => setFormData({ ...formData, kpiCode: e.target.value.toUpperCase() })}
                placeholder="CUSTOM-GPU-TEMP"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
              {errors.kpiCode && (
                <p className="text-sm text-red-600 mt-1">{errors.kpiCode}</p>
              )}
              <p className="text-xs text-gray-500 mt-1">
                Must start with CUSTOM-, alphanumeric and hyphens only
              </p>
            </div>

            {/* Pillar */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Pillar *
              </label>
              <select
                value={formData.pillar}
                onChange={(e) => setFormData({ ...formData, pillar: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="AI">AI Workload Performance</option>
                <option value="CH">Customer Health</option>
                <option value="DV">Deployment Velocity</option>
                <option value="EX">Expansion & Growth</option>
                <option value="OS">Operational Stability</option>
              </select>
            </div>

            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Display Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="GPU Temperature"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
              {errors.name && (
                <p className="text-sm text-red-600 mt-1">{errors.name}</p>
              )}
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Average GPU temperature across all nodes"
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>

            {/* Unit */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Unit *
              </label>
              <select
                value={formData.unit}
                onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="%">%</option>
                <option value="°C">°C</option>
                <option value="°F">°F</option>
                <option value="watts">watts</option>
                <option value="count">count</option>
                <option value="hours">hours</option>
                <option value="days">days</option>
                <option value="ms">ms</option>
                <option value="MB/s">MB/s</option>
                <option value="GB">GB</option>
                <option value="$K">$K</option>
                <option value="score">score</option>
              </select>
            </div>

            {/* Target & Operator */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Target Value *
                </label>
                <input
                  type="number"
                  step="any"
                  value={formData.target}
                  onChange={(e) => setFormData({ ...formData, target: e.target.value })}
                  placeholder="75.0"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
                {errors.target && (
                  <p className="text-sm text-red-600 mt-1">{errors.target}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Operator *
                </label>
                <select
                  value={formData.operator}
                  onChange={(e) => setFormData({ ...formData, operator: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value=">">Greater than (&gt;)</option>
                  <option value="<">Less than (&lt;)</option>
                  <option value=">=">Greater or equal (≥)</option>
                  <option value="<=">Less or equal (≤)</option>
                  <option value="=">Equal (=)</option>
                </select>
              </div>
            </div>

            {/* Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Acceptable Range *
              </label>
              <div className="grid grid-cols-2 gap-4">
                <input
                  type="number"
                  step="any"
                  value={formData.rangeMin}
                  onChange={(e) => setFormData({ ...formData, rangeMin: e.target.value })}
                  placeholder="Min (e.g., 60)"
                  className="px-3 py-2 border border-gray-300 rounded-md"
                />
                <input
                  type="number"
                  step="any"
                  value={formData.rangeMax}
                  onChange={(e) => setFormData({ ...formData, rangeMax: e.target.value })}
                  placeholder="Max (e.g., 85)"
                  className="px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              {errors.range && (
                <p className="text-sm text-red-600 mt-1">{errors.range}</p>
              )}
            </div>

            {/* Submit Error */}
            {errors.submit && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-600">{errors.submit}</p>
              </div>
            )}

            {/* Buttons */}
            <div className="flex justify-end space-x-3 pt-4 border-t">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                disabled={saving}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Custom KPI'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
