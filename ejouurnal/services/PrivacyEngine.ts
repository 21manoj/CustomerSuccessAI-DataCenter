/**
 * PrivacyEngine - Privacy-preserving aggregation and encryption
 * 
 * Core principles:
 * 1. Local-first: All sensitive data processed on-device
 * 2. Zero-knowledge: Server never sees unencrypted personal data
 * 3. Differential privacy: Aggregate insights without exposing individuals
 * 4. User control: Explicit opt-in for cloud sync, easy export/delete
 * 
 * Encryption layers:
 * - Layer 1: Device storage (SQLCipher)
 * - Layer 2: Cloud sync (E2E encryption)
 * - Layer 3: Journals (Extra encryption)
 */

import CryptoJS from 'crypto-js';

interface EncryptionKeys {
  masterKey: string; // Derived from user's passcode
  journalKey: string; // Separate key for extra-sensitive journals
  cloudKey: string; // For cloud sync
}

export class PrivacyEngine {
  private keys: EncryptionKeys | null = null;

  /**
   * Initialize encryption keys from user passcode
   * Uses PBKDF2 for key derivation
   */
  async initializeKeys(userPasscode: string, userId: string): Promise<void> {
    // Derive master key from passcode + userId salt
    const masterKey = CryptoJS.PBKDF2(userPasscode, userId, {
      keySize: 256 / 32,
      iterations: 100000
    }).toString();

    // Derive separate journal key
    const journalKey = CryptoJS.PBKDF2(userPasscode + '-journal', userId, {
      keySize: 256 / 32,
      iterations: 100000
    }).toString();

    // Cloud sync key (can be rotated independently)
    const cloudKey = CryptoJS.PBKDF2(userPasscode + '-cloud', userId + Date.now(), {
      keySize: 256 / 32,
      iterations: 100000
    }).toString();

    this.keys = { masterKey, journalKey, cloudKey };
  }

  /**
   * LAYER 1: Local Storage Encryption (SQLCipher)
   */
  encryptForLocalStorage(data: any, dataType: 'check-in' | 'journal' | 'settings'): string {
    if (!this.keys) throw new Error('Encryption keys not initialized');

    const key = dataType === 'journal' ? this.keys.journalKey : this.keys.masterKey;
    const serialized = JSON.stringify(data);
    
    return CryptoJS.AES.encrypt(serialized, key).toString();
  }

  decryptFromLocalStorage(encrypted: string, dataType: 'check-in' | 'journal' | 'settings'): any {
    if (!this.keys) throw new Error('Encryption keys not initialized');

    const key = dataType === 'journal' ? this.keys.journalKey : this.keys.masterKey;
    const decrypted = CryptoJS.AES.decrypt(encrypted, key);
    
    return JSON.parse(decrypted.toString(CryptoJS.enc.Utf8));
  }

  /**
   * LAYER 2: Cloud Sync Encryption (End-to-End)
   * Server never sees unencrypted data
   */
  encryptForCloudSync(data: any): {
    encrypted: string;
    iv: string;
    authTag: string;
  } {
    if (!this.keys) throw new Error('Encryption keys not initialized');

    const serialized = JSON.stringify(data);
    const iv = CryptoJS.lib.WordArray.random(128 / 8).toString();
    
    const encrypted = CryptoJS.AES.encrypt(serialized, this.keys.cloudKey, {
      iv: CryptoJS.enc.Hex.parse(iv),
      mode: CryptoJS.mode.CBC,
      padding: CryptoJS.pad.Pkcs7
    });

    return {
      encrypted: encrypted.toString(),
      iv: iv,
      authTag: this.generateAuthTag(encrypted.toString(), iv)
    };
  }

  decryptFromCloudSync(payload: {
    encrypted: string;
    iv: string;
    authTag: string;
  }): any {
    if (!this.keys) throw new Error('Encryption keys not initialized');

    // Verify auth tag
    const expectedTag = this.generateAuthTag(payload.encrypted, payload.iv);
    if (expectedTag !== payload.authTag) {
      throw new Error('Data integrity check failed');
    }

    const decrypted = CryptoJS.AES.decrypt(payload.encrypted, this.keys.cloudKey, {
      iv: CryptoJS.enc.Hex.parse(payload.iv),
      mode: CryptoJS.mode.CBC,
      padding: CryptoJS.pad.Pkcs7
    });

    return JSON.parse(decrypted.toString(CryptoJS.enc.Utf8));
  }

  /**
   * DIFFERENTIAL PRIVACY: Aggregate insights without exposing individuals
   * 
   * Used for "network effects" - learn from all users without seeing their data
   */
  async contributeToDifferentialPrivacy(
    localInsights: any[],
    userId: string
  ): Promise<void> {
    // Add noise to prevent re-identification
    const noisyInsights = localInsights.map(insight => ({
      ...insight,
      impact: this.addLaplaceNoise(insight.impact, 1.0), // epsilon = 1.0
      count: Math.max(1, Math.floor(this.addLaplaceNoise(1, 0.5)))
    }));

    // Remove all PII
    const anonymized = noisyInsights.map(insight => ({
      type: insight.type,
      sourceMetric: insight.sourceMetric,
      targetMetric: insight.targetMetric,
      impact: insight.impact,
      confidence: insight.confidence,
      // NO userId, NO timestamps, NO personal details
    }));

    // Send to aggregation server
    await this.sendToAggregationServer(anonymized);
  }

  /**
   * Receive aggregated insights from server (already anonymized)
   */
  async fetchAggregatedInsights(userProfile: {
    ageGroup?: string;
    goals?: string[];
  }): Promise<any[]> {
    // Server returns insights like:
    // "Users similar to you see +12 MindScore after morning walks"
    // NO individual data is exposed
    
    return [
      {
        type: 'aggregate',
        title: 'Most users benefit from morning movement',
        description: 'Users with similar patterns show +10-15 MindScore boost from 30+ min morning activity',
        sampleSize: '1,247 users', // Always >1000 to prevent re-identification
        confidence: 'high'
      }
    ];
  }

  /**
   * LAPLACE NOISE for Differential Privacy
   */
  private addLaplaceNoise(value: number, sensitivity: number): number {
    const u = Math.random() - 0.5;
    const noise = -sensitivity * Math.sign(u) * Math.log(1 - 2 * Math.abs(u));
    return value + noise;
  }

  /**
   * SECURE DATA EXPORT
   * User owns their data - export everything
   */
  async exportAllData(format: 'json' | 'csv' | 'pdf'): Promise<Blob> {
    // Decrypt all data
    const allData = {
      checkIns: await this.getAllCheckIns(),
      journals: await this.getAllJournals(),
      bodyMetrics: await this.getAllBodyMetrics(),
      scores: await this.getAllScores(),
      insights: await this.getAllInsights()
    };

    if (format === 'json') {
      return new Blob([JSON.stringify(allData, null, 2)], { type: 'application/json' });
    } else if (format === 'csv') {
      return this.convertToCSV(allData);
    } else {
      return this.generatePDF(allData);
    }
  }

  /**
   * SECURE DELETE
   * Delete all user data (GDPR compliance)
   */
  async deleteAllData(confirmation: string): Promise<void> {
    if (confirmation !== 'DELETE ALL MY DATA') {
      throw new Error('Invalid confirmation');
    }

    // Delete from local storage
    await this.deleteLocalDatabase();

    // Delete from cloud (if synced)
    await this.deleteCloudData();

    // Clear encryption keys
    this.keys = null;
  }

  /**
   * DATA MINIMIZATION
   * Only store what's needed for insights
   */
  minimizeData(rawData: any): any {
    // Remove:
    // - Exact timestamps (only store date + daypart)
    // - IP addresses
    // - Device identifiers (beyond what's needed for sync)
    // - Free-form text (unless explicitly saved as journal)
    
    return {
      date: rawData.timestamp?.toDateString(),
      dayPart: rawData.dayPart,
      mood: rawData.mood,
      contexts: rawData.contexts,
      microAct: rawData.microAct,
      // NO: exact GPS, IP, device ID, free text notes (unless journal)
    };
  }

  /**
   * CONSENT MANAGEMENT
   * Explicit user control over what's collected and shared
   */
  async updateConsent(consent: {
    collectDeviceData: boolean;
    cloudSync: boolean;
    anonymousAggregation: boolean;
    shareWithCoach: boolean;
  }): Promise<void> {
    // Store consent preferences (encrypted)
    await this.storeEncrypted('consent', consent);

    // If user revokes cloud sync, delete cloud data
    if (!consent.cloudSync) {
      await this.deleteCloudData();
    }

    // If user revokes aggregation, stop contributing
    if (!consent.anonymousAggregation) {
      await this.optOutOfAggregation();
    }
  }

  /**
   * HELPER: Generate authentication tag
   */
  private generateAuthTag(encrypted: string, iv: string): string {
    return CryptoJS.HmacSHA256(encrypted + iv, this.keys!.cloudKey).toString();
  }

  /**
   * HELPER: Send to aggregation server
   */
  private async sendToAggregationServer(data: any[]): Promise<void> {
    // In production: POST to /api/aggregate
    // Server stores ONLY anonymized counts, never individual records
    console.log('Contributing to differential privacy pool:', data.length, 'insights');
  }

  /**
   * PLACEHOLDER: Storage methods (implement with SQLite + SQLCipher)
   */
  private async getAllCheckIns(): Promise<any[]> { return []; }
  private async getAllJournals(): Promise<any[]> { return []; }
  private async getAllBodyMetrics(): Promise<any[]> { return []; }
  private async getAllScores(): Promise<any[]> { return []; }
  private async getAllInsights(): Promise<any[]> { return []; }
  private async deleteLocalDatabase(): Promise<void> {}
  private async deleteCloudData(): Promise<void> {}
  private async storeEncrypted(key: string, data: any): Promise<void> {}
  private async optOutOfAggregation(): Promise<void> {}
  private convertToCSV(data: any): Blob { return new Blob(); }
  private generatePDF(data: any): Blob { return new Blob(); }
}

export default PrivacyEngine;

