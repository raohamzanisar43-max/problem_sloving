import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, FlatList, StyleSheet, ActivityIndicator, TouchableOpacity, Alert, RefreshControl } from 'react-native';
import apiClient from '../api/apiClient';

const INTENT_LABELS = [
  { label: 'Buyer', value: 'buyer' },
  { label: 'Hiring', value: 'hiring' },
  { label: 'Non-buyer', value: 'nonbuyer' },
  { label: 'Uncertain', value: 'uncertain' },
];

export default function ReviewScreen({ navigation }: any) {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actingId, setActingId] = useState<string | null>(null);

  const loadReviewQueue = useCallback((isRefresh = false) => {
    if (isRefresh) setRefreshing(true); else setLoading(true);
    apiClient.get('/opportunities/', { params: { status: 'review' } })
      .then((res) => setItems(res.data.results ?? res.data))
      .catch((err) => console.log('Error loading review queue:', err.message))
      .finally(() => {
        setLoading(false);
        setRefreshing(false);
      });
  }, []);

  useEffect(() => {
    loadReviewQueue();
  }, [loadReviewQueue]);

  const onRefresh = () => {
    loadReviewQueue(true);
  };

  const handleAction = async (id: string, newStatus: 'new' | 'rejected') => {
    setActingId(id);
    try {
      const detail = await apiClient.get(`/opportunities/${id}/`);
      await apiClient.patch(`/opportunities/${id}/`, {
        status: newStatus,
        expected_revision: detail.data.revision,
      });
      setItems((prev) => prev.filter((o) => o.id !== id));
    } catch (err: any) {
      Alert.alert('Error', 'Update failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setActingId(null);
    }
  };

  if (loading) return <ActivityIndicator style={{ flex: 1 }} size="large" />;

  return (
    <View style={styles.container}>
      <FlatList
        data={items}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={styles.list}
        ListEmptyComponent={<Text style={styles.empty}>No opportunities pending review.</Text>}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <TouchableOpacity onPress={() => navigation.navigate('LeadDetail', { id: item.id })}>
              <Text style={styles.title}>{item.requirement ?? 'Untitled'}</Text>
              <Text style={styles.meta}>{item.band} · Score {item.score}</Text>
            </TouchableOpacity>

            <View style={styles.intentRow}>
              {INTENT_LABELS.map((opt) => (
                <View
                  key={opt.value}
                  style={[styles.intentChip, item.intent === opt.value && styles.intentChipActive]}
                >
                  <Text style={[styles.intentChipText, item.intent === opt.value && styles.intentChipTextActive]}>
                    {opt.label}
                  </Text>
                </View>
              ))}
            </View>
            <Text style={styles.confidence}>AI confidence: {Math.round((item.confidence ?? 0) * 100)}%</Text>

            {item.review_reasons?.length > 0 && (
              <View style={styles.reasonsRow}>
                {item.review_reasons.map((r: string, i: number) => (
                  <Text key={i} style={styles.reasonChip}>{r}</Text>
                ))}
              </View>
            )}

            <View style={styles.actionsRow}>
              <TouchableOpacity
                style={styles.rejectButton}
                disabled={actingId === item.id}
                onPress={() => handleAction(item.id, 'rejected')}
              >
                <Text style={styles.rejectButtonText}>Reject</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.approveButton}
                disabled={actingId === item.id}
                onPress={() => handleAction(item.id, 'new')}
              >
                {actingId === item.id ? (
                  <ActivityIndicator color="#fff" size="small" />
                ) : (
                  <Text style={styles.approveButtonText}>Approve</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f3ee' },
  list: { padding: 16 },
  empty: { textAlign: 'center', marginTop: 40, color: '#6b7873' },
  card: { backgroundColor: '#fff', borderRadius: 10, padding: 14, marginBottom: 14, borderWidth: 1, borderColor: '#e3e0d8' },
  title: { fontSize: 15, fontWeight: '600', color: '#10201c', marginBottom: 4 },
  meta: { fontSize: 12, color: '#4b5f5a', marginBottom: 10 },
  intentRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 8 },
  intentChip: { paddingVertical: 5, paddingHorizontal: 10, borderRadius: 14, borderWidth: 1, borderColor: '#d3ddd9', backgroundColor: '#f5f3ee' },
  intentChipActive: { backgroundColor: '#0f8a5f', borderColor: '#0f8a5f' },
  intentChipText: { fontSize: 12, color: '#4b5f5a' },
  intentChipTextActive: { color: '#fff', fontWeight: '600' },
  confidence: { fontSize: 12, color: '#6b7873', marginBottom: 10 },
  reasonsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 12 },
  reasonChip: { fontSize: 11, color: '#9b3b3b', backgroundColor: '#f7e8e8', paddingVertical: 4, paddingHorizontal: 8, borderRadius: 10 },
  actionsRow: { flexDirection: 'row', gap: 10 },
  rejectButton: { flex: 1, padding: 12, borderRadius: 8, borderWidth: 1, borderColor: '#9b3b3b', alignItems: 'center' },
  rejectButtonText: { color: '#9b3b3b', fontWeight: '600' },
  approveButton: { flex: 1, padding: 12, borderRadius: 8, backgroundColor: '#0f8a5f', alignItems: 'center' },
  approveButtonText: { color: '#fff', fontWeight: '600' },
});