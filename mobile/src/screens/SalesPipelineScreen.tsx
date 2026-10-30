import React, { useEffect, useState, useCallback } from 'react';
import { Text, SectionList, StyleSheet, ActivityIndicator, TouchableOpacity, RefreshControl } from 'react-native';
import apiClient from '../api/apiClient';

const STAGES = [
  { key: 'new', label: 'New' },
  { key: 'review', label: 'Reviewed' },
  { key: 'contacted', label: 'Contacted' },
  { key: 'closed', label: 'Closed (Won)' },
  { key: 'rejected', label: 'Rejected (Lost)' },
];

export default function SalesPipelineScreen({ navigation }: any) {
  const [sections, setSections] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadPipeline = useCallback(async () => {
    try {
      const responses = await Promise.all(
        STAGES.map((stage) =>
          apiClient.get('/opportunities/', { params: { status: stage.key, ordering: '-detected_at' } })
        )
      );
      const built = STAGES.map((stage, i) => ({
        title: `${stage.label} (${responses[i].data.count ?? 0})`,
        stageKey: stage.key,
        data: responses[i].data.results ?? responses[i].data,
      }));
      setSections(built);
    } catch (err: any) {
      console.log('Error loading pipeline:', err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadPipeline();
  }, [loadPipeline]);

  const onRefresh = () => {
    setRefreshing(true);
    loadPipeline();
  };

  if (loading) return <ActivityIndicator style={{ flex: 1 }} size="large" />;

  return (
    <SectionList
      style={styles.container}
      contentContainerStyle={styles.list}
      sections={sections}
      keyExtractor={(item) => String(item.id)}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      renderSectionHeader={({ section }) => <Text style={styles.sectionHeader}>{section.title}</Text>}
      renderItem={({ item }) => (
        <TouchableOpacity style={styles.card} onPress={() => navigation.navigate('LeadDetail', { id: item.id })}>
          <Text style={styles.cardTitle}>{item.requirement ?? 'Untitled'}</Text>
          <Text style={styles.cardMeta}>{item.band} · Score {item.score}</Text>
        </TouchableOpacity>
      )}
      renderSectionFooter={({ section }) =>
        section.data.length === 0 ? (
          <Text style={styles.emptyStage}>No opportunities in this stage.</Text>
                ) : null
      }
      stickySectionHeadersEnabled
    />
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f3ee' },
  list: { padding: 16, paddingBottom: 32 },
  sectionHeader: { fontSize: 15, fontWeight: '700', color: '#10201c', backgroundColor: '#f5f3ee', paddingVertical: 10 },
  emptyStage: { fontSize: 12, color: '#9aa39e', marginBottom: 14, fontStyle: 'italic' },
  card: { backgroundColor: '#fff', borderRadius: 10, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: '#e3e0d8' },
  cardTitle: { fontSize: 14, fontWeight: '600', color: '#10201c', marginBottom: 4 },
  cardMeta: { fontSize: 12, color: '#4b5f5a' },
});