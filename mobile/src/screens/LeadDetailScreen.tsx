import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, ScrollView, StyleSheet, ActivityIndicator, TouchableOpacity, Linking, Alert, Share } from 'react-native';
import apiClient from '../api/apiClient';

const FACTOR_LABELS = [
  { label: 'Buying intent', max: 30 },
  { label: 'Service match', max: 25 },
  { label: 'Recency', max: 15 },
  { label: 'Evidence quality', max: 15 },
  { label: 'Contact path', max: 10 },
  { label: 'Deadline urgency', max: 5 },
];

const BAND_COLORS: Record<string, string> = {
  'Hot': '#0f8a5f',
  'High potential': '#c2680a',
  'Review': '#4b5f5a',
  'Archive': '#9b3b3b',
};

export default function LeadDetailScreen({ route }: any) {
  const { id } = route.params;
  const [opp, setOpp] = useState<any>(null);
  const [me, setMe] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);

  const loadOpportunity = useCallback(() => {
    return apiClient.get(`/opportunities/${id}/`)
      .then((res) => setOpp(res.data))
      .catch((err) => console.log('Error fetching detail:', err.message));
  }, [id]);

  useEffect(() => {
    Promise.all([
      loadOpportunity(),
      apiClient.get('/me/').then((res) => setMe(res.data)).catch((err) => console.log('Error fetching account:', err.message)),
    ]).finally(() => setLoading(false));
  }, [loadOpportunity]);

  const patchOpportunity = async (body: Record<string, any>) => {
    setUpdating(true);
    try {
      const res = await apiClient.patch(`/opportunities/${id}/`, {
        ...body,
        expected_revision: opp.revision,
      });
      setOpp(res.data);
    } catch (err: any) {
      Alert.alert('Error', 'Update failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUpdating(false);
    }
  };

  const handleAssignToMe = () => {
    if (!me) return;
    patchOpportunity({ owner: me.id });
  };

  const handleStatusChange = (newStatus: string, label: string) => {
    Alert.alert(`Mark as ${label}?`, `This will change the opportunity's status to "${label}".`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Confirm', onPress: () => patchOpportunity({ status: newStatus }) },
    ]);
  };

  const handleShare = async () => {
    const lines = [
      opp.requirement ?? 'Opportunity',
      `Score: ${opp.score} · ${opp.band}`,
      opp.company_name ? `Company: ${opp.company_name}` : null,
      opp.company_website ? `Website: ${opp.company_website}` : null,
      opp.country ? `Country: ${opp.country}` : null,
      opp.budget_text ? `Budget: ${opp.budget_text}` : null,
      opp.deadline ? `Deadline: ${opp.deadline}` : null,
      opp.email ? `Email: ${opp.email}` : null,
      opp.phone ? `Phone: ${opp.phone}` : null,
      opp.source_url ? `Source: ${opp.source_url}` : null,
    ].filter(Boolean);

    try {
      await Share.share({
        message: lines.join('\n'),
        title: opp.requirement ?? 'Novu Opportunity Radar lead',
      });
    } catch (err: any) {
      Alert.alert('Error', 'Could not open share sheet: ' + err.message);
    }
  };

  if (loading) return <ActivityIndicator style={{ flex: 1 }} size="large" />;
  if (!opp) return <Text style={styles.error}>Opportunity load nahi hui.</Text>;

  const bandColor = BAND_COLORS[opp.band] ?? '#4b5f5a';
  const factors: number[] = opp.score_factors ?? [];

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>{opp.requirement}</Text>

      <View style={styles.badgeRow}>
        <View style={[styles.badge, { backgroundColor: bandColor }]}>
          <Text style={styles.badgeText}>{opp.score} · {opp.band}</Text>
        </View>
        <View style={[styles.badge, styles.statusBadge]}>
          <Text style={styles.statusBadgeText}>{opp.status}</Text>
        </View>
      </View>

      {/* Score breakdown */}
      <Text style={styles.sectionTitle}>Score Breakdown</Text>
      {FACTOR_LABELS.map((f, i) => (
        <View key={f.label} style={styles.factorRow}>
          <Text style={styles.factorLabel}>{f.label}</Text>
          <View style={styles.factorBarTrack}>
            <View style={[styles.factorBarFill, { width: `${((factors[i] ?? 0) / f.max) * 100}%` }]} />
          </View>
          <Text style={styles.factorValue}>{factors[i] ?? 0}/{f.max}</Text>
        </View>
      ))}

      {/* AI classification */}
      <Text style={styles.sectionTitle}>AI Classification</Text>
      <Row label="Intent" value={opp.intent} />
      <Row label="Kind" value={opp.kind} />
      <Row label="Confidence" value={`${Math.round((opp.confidence ?? 0) * 100)}%`} />

      {opp.intent_evidence ? (
        <View style={styles.quoteBox}>
          <Text style={styles.quoteText}>"{opp.intent_evidence}"</Text>
        </View>
      ) : null}

      {opp.review_reasons?.length > 0 && (
        <View style={styles.reasonsBox}>
          {opp.review_reasons.map((r: string, idx: number) => (
            <Text key={idx} style={styles.reasonChip}>⚠ {r}</Text>
          ))}
        </View>
      )}

      {/* Company */}
      <Text style={styles.sectionTitle}>Company</Text>
      <Row label="Company" value={opp.company_name || '—'} />
      <Row label="Website" value={opp.company_website || '—'} />
      <Row label="Country" value={opp.country || '—'} />
      <Row label="Budget" value={opp.budget_text || '—'} />
      <Row label="Deadline" value={opp.deadline || '—'} />

      {/* Contact */}
      {(opp.email || opp.phone) && (
        <>
          <Text style={styles.sectionTitle}>Contact</Text>
          {opp.email ? <Row label="Email" value={opp.email} /> : null}
          {opp.phone ? <Row label="Phone" value={opp.phone} /> : null}
          {opp.contact_verification ? <Row label="Verification" value={opp.contact_verification} /> : null}
        </>
      )}

      {/* Pipeline & Ownership */}
      <Text style={styles.sectionTitle}>Pipeline & Ownership</Text>
      <Row label="Owner" value={opp.owner_name || 'Unassigned'} />
      {!opp.owner && (
        <TouchableOpacity style={styles.assignButton} disabled={updating} onPress={handleAssignToMe}>
          <Text style={styles.assignButtonText}>Assign to me</Text>
        </TouchableOpacity>
      )}

      <View style={styles.pipelineActionsRow}>
        {opp.status !== 'contacted' && (
          <TouchableOpacity
            style={styles.pipelineButton}
            disabled={updating}
            onPress={() => handleStatusChange('contacted', 'Contacted')}
          >
            <Text style={styles.pipelineButtonText}>Mark Contacted</Text>
          </TouchableOpacity>
        )}
        {opp.status !== 'closed' && (
          <TouchableOpacity
            style={[styles.pipelineButton, styles.pipelineButtonWon]}
            disabled={updating}
            onPress={() => handleStatusChange('closed', 'Closed (Won)')}
          >
            <Text style={styles.pipelineButtonText}>Close as Won</Text>
          </TouchableOpacity>
        )}
        {opp.status !== 'rejected' && (
          <TouchableOpacity
            style={[styles.pipelineButton, styles.pipelineButtonLost]}
            disabled={updating}
            onPress={() => handleStatusChange('rejected', 'Rejected (Lost)')}
          >
            <Text style={styles.pipelineButtonText}>Close as Lost</Text>
          </TouchableOpacity>
        )}
      </View>
      {updating && <ActivityIndicator style={{ marginTop: 8 }} />}

      {/* Source */}
      {opp.source_url ? (
        <TouchableOpacity style={styles.sourceButton} onPress={() => Linking.openURL(opp.source_url)}>
          <Text style={styles.sourceButtonText}>Open Original Source →</Text>
        </TouchableOpacity>
      ) : null}

      <TouchableOpacity style={styles.shareButton} onPress={handleShare}>
        <Text style={styles.shareButtonText}>Share Opportunity</Text>
      </TouchableOpacity>

      <View style={{ height: 30 }} />
    </ScrollView>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f3ee', padding: 16 },
  error: { flex: 1, textAlign: 'center', marginTop: 40 },
  title: { fontSize: 19, fontWeight: '700', marginBottom: 10, color: '#10201c' },
  badgeRow: { flexDirection: 'row', gap: 8, marginBottom: 20 },
  badge: { paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999 },
  badgeText: { color: '#fff', fontWeight: '700', fontSize: 12 },
  statusBadge: { backgroundColor: '#e3ece9', borderWidth: 1, borderColor: '#d3ddd9' },
  statusBadgeText: { color: '#10201c', fontWeight: '600', fontSize: 12, textTransform: 'capitalize' },
  sectionTitle: { fontSize: 13, fontWeight: '700', color: '#0f8a5f', marginTop: 18, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  factorRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8, gap: 8 },
  factorLabel: { width: 110, fontSize: 12, color: '#4b5f5a' },
  factorBarTrack: { flex: 1, height: 8, borderRadius: 4, backgroundColor: '#e3ece9', overflow: 'hidden' },
  factorBarFill: { height: '100%', backgroundColor: '#0f8a5f' },
  factorValue: { width: 42, fontSize: 11, color: '#4b5f5a', textAlign: 'right' },
  quoteBox: { backgroundColor: '#fff', borderLeftWidth: 3, borderLeftColor: '#0f8a5f', padding: 12, borderRadius: 6, marginTop: 4 },
  quoteText: { fontStyle: 'italic', fontSize: 13, color: '#10201c' },
  reasonsBox: { marginTop: 8, gap: 4 },
  reasonChip: { fontSize: 12, color: '#c2680a', backgroundColor: '#fbeedd', padding: 6, borderRadius: 6 },
  row: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: '#e3ece9' },
  rowLabel: { fontSize: 13, color: '#4b5f5a' },
  rowValue: { fontSize: 13, color: '#10201c', fontWeight: '600', maxWidth: '60%', textAlign: 'right' },
  assignButton: { marginTop: 8, alignSelf: 'flex-start', paddingVertical: 6, paddingHorizontal: 12, borderRadius: 8, borderWidth: 1, borderColor: '#0f8a5f' },
  assignButtonText: { color: '#0f8a5f', fontWeight: '600', fontSize: 12 },
  pipelineActionsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  pipelineButton: { flexGrow: 1, paddingVertical: 10, paddingHorizontal: 12, borderRadius: 8, backgroundColor: '#2a5d8f', alignItems: 'center' },
  pipelineButtonWon: { backgroundColor: '#0f8a5f' },
  pipelineButtonLost: { backgroundColor: '#9b3b3b' },
  pipelineButtonText: { color: '#fff', fontWeight: '600', fontSize: 12 },
  sourceButton: { marginTop: 20, backgroundColor: '#0f8a5f', borderRadius: 8, padding: 14, alignItems: 'center' },
  sourceButtonText: { color: '#fff', fontWeight: '700' },
  shareButton: { marginTop: 12, backgroundColor: '#fff', borderWidth: 1, borderColor: '#0f8a5f', borderRadius: 8, padding: 14, alignItems: 'center' },
  shareButtonText: { color: '#0f8a5f', fontWeight: '700' },
});