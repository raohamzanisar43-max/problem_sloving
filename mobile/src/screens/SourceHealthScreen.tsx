import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, FlatList, StyleSheet, ActivityIndicator, RefreshControl } from 'react-native';
import apiClient from '../api/apiClient';

function getHealth(source: any) {
  if (source.last_error) return { label: 'Error', color: '#9b3b3b' };
  if (!source.enabled) return { label: 'Not enabled', color: '#c2680a' };
  return { label: 'Working', color: '#0f8a5f' };
}

export default function SourceHealthScreen() {
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadSources = useCallback(() => {
    apiClient.get('/sources/')
      .then((res) => setSources(res.data.results ?? res.data))
      .catch((err) => console.log('Error loading sources:', err.message))
      .finally(() => {
        setLoading(false);
        setRefreshing(false);
      });
  }, []);

  useEffect(() => {
    loadSources();
  }, [loadSources]);

  const onRefresh = () => {
    setRefreshing(true);
    loadSources();
  };

  if (loading) return <ActivityIndicator style={{ flex: 1 }} size="large" />;

  return (
    <FlatList
      style={styles.container}
      contentContainerStyle={styles.list}
      data={sources}
      keyExtractor={(item) => item.id}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      renderItem={({ item }) => {
        const health = getHealth(item);
        return (
          <View style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.name}>{item.name}</Text>
              <View style={styles.statusRow}>
                <View style={[styles.dot, { backgroundColor: health.color }]} />
                <Text style={[styles.statusText, { color: health.color }]}>{health.label}</Text>
              </View>
            </View>
            <Text style={styles.meta}>{item.connector_type.toUpperCase()} · {item.planned_route}</Text>
            <Text style={styles.meta}>
              {item.last_success_at
                ? `Last successful run: ${new Date(item.last_success_at).toLocaleString()}`
 : 'Never run yet'}
             </Text>
            {item.last_error ? <Text style={styles.error}>{item.last_error}</Text> : null}
          </View>
        );
      }}
    />
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f3ee' },
  list: { padding: 16 },
  card: { backgroundColor: '#fff', borderRadius: 10, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: '#e3e0d8' },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  name: { fontSize: 15, fontWeight: '600', color: '#10201c' },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  statusText: { fontSize: 12, fontWeight: '600' },
  meta: { fontSize: 12, color: '#4b5f5a', marginTop: 2 },
  error: { fontSize: 12, color: '#9b3b3b', marginTop: 4 },
});