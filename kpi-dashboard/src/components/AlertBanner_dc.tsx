/**
 * Data Center Alert Banner Component
 * Displays alerts and notifications for DC tenants
 */

import React, { useState, useEffect } from 'react';
import { AlertTriangle, X, CheckCircle, Info } from 'lucide-react';
import { useSession } from '../contexts/SessionContext';

interface Alert {
  alert_id: string;
  kpi_id: string;
  kpi_name: string;
  severity: 'critical' | 'warning' | 'info';
  message: string;
  timestamp: string;
}

interface AlertBannerProps {
  tenantId: number | null;
}

const AlertBanner_dc: React.FC<AlertBannerProps> = ({ tenantId }) => {
  const { session } = useSession();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(false);
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (tenantId) {
      loadAlerts();
    }
  }, [tenantId]);

  const loadAlerts = async () => {
    if (!tenantId) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/dc/alerts/${tenantId}`, {
        credentials: 'include',
        headers: {
          'X-Customer-ID': session?.customer_id?.toString() || '',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setAlerts(data.alerts || []);
      }
    } catch (error) {
      console.error('Error loading alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  const dismissAlert = (alertId: string) => {
    setDismissedAlerts(prev => new Set(prev).add(alertId));
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertTriangle className="h-5 w-5 text-red-600" />;
      case 'warning':
        return <AlertTriangle className="h-5 w-5 text-yellow-600" />;
      case 'info':
        return <Info className="h-5 w-5 text-blue-600" />;
      default:
        return <Info className="h-5 w-5 text-gray-600" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-50 border-red-200 text-red-800';
      case 'warning':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800';
      case 'info':
        return 'bg-blue-50 border-blue-200 text-blue-800';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-16 bg-gray-200 rounded"></div>
            <div className="h-16 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  const visibleAlerts = alerts.filter(alert => !dismissedAlerts.has(alert.alert_id));

  if (visibleAlerts.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center py-12">
          <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Active Alerts</h3>
          <p className="text-gray-500">
            {tenantId ? 'All systems operational for this tenant.' : 'Select a tenant to view alerts.'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Active Alerts ({visibleAlerts.length})
          </h2>
        </div>
        <div className="space-y-3">
          {visibleAlerts.map((alert) => (
            <div
              key={alert.alert_id}
              className={`border rounded-lg p-4 ${getSeverityColor(alert.severity)}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3 flex-1">
                  {getSeverityIcon(alert.severity)}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold">{alert.kpi_name}</span>
                      <span className="text-xs opacity-75 capitalize">({alert.severity})</span>
                    </div>
                    <p className="text-sm opacity-90">{alert.message}</p>
                    <p className="text-xs opacity-75 mt-1">
                      {new Date(alert.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => dismissAlert(alert.alert_id)}
                  className="ml-4 text-gray-400 hover:text-gray-600"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AlertBanner_dc;

