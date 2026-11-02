import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, FlatList, StyleSheet, ActivityIndicator, TouchableOpacity, RefreshControl } from 'react-native';
import apiClient from '../api/apiClient';

const BAND_COLORS: Record<string, string> = {
  'Hot': '#0f8a5f',
  'High potential': '#c2680a',
  'Review': '#4b5f5a',
  'Archive': '#9b3b3b',
};

const EMPTY_FILTERS = {
  intent: null as string | null,
  status: null as string | null,
  band: null as string | null,
  category: null as string | null,
  source: null as string | null,
  minScore: 0,
  datePreset: 'any' as 'any' | '24h' | '7d' | '30d',
};

function activeFilterCount(f: typeof EMPTY_FILTERS) {
  let n = 0;
  if (f.intent) n++;
  if (f.status) n++;
  if (f.band) n++;
  if (f.category) n++;
  if (f.source) n++;
  if (f.minScore > 0) n++;
  if (f.datePreset !== 'any') n++;
  return n;
}

export default function OpportunityQueueScreen({ navigation, route }: any) {
  const [rawOpportunities, setRawOpportunities] = useState<any[]>([]);
  const [nextUrl, setNextUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [categoryOptions, setCategoryOptions] = useState<string[]>([]);
  const [sourceOptions, setSourceOptions] = useState<string[]>([]);

  const fetchOpportunities = useCallback(
    (isRefresh = false) => {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);

      const params: Record<string, string> = { ordering: '-score' };
      if (filters.intent) params.intent = filters.intent;
      if (filters.status) params.status = filters.status;
      if (filters.band) params.band = filters.band;

      apiClient
        .get('/opportunities/', { params })
        .then((res) => {
          const results = res.data.results ?? res.data;
          setRawOpportunities(results);
          setNextUrl(res.data.next ?? null);
          if (categoryOptions.length === 0 && sourceOptions.length === 0) {
            setCategoryOptions([...new Set(results.map((o: any) => o.primary_category).filter(Boolean))] as string[]);
            setSourceOptions([...new Set(results.map((o: any) => o.source_name).filter(Boolean))] as string[]);
          }
        })
        .catch((err) => console.log('Error fetching opportunities:', err.message))
        .finally(() => {
          setLoading(false);
          setRefreshing(false);
        });
    },
    [filters.intent, filters.status, filters.band]
  );

  useEffect(() => {
    fetchOpportunities();
  }, [fetchOpportunities]);

  useEffect(() => {
    if (route.params?.filters) {
      setFilters(route.params.filters);
    }
  }, [route.params?.filters]);

  useEffect(() => {
    navigation.setOptions({
      headerRight: () => (
        <TouchableOpacity
          onPress={() => navigation.navigate('Filters', { filters, categoryOptions, sourceOptions })}
          style={{ paddingHorizontal: 12 }}
        >
          <Text style={{ color: '#0f8a5f', fontWeight: '600' }}>
            Filters{activeFilterCount(filters) > 0 ? ` (${activeFilterCount(filters)})` : ''}
          </Text>
        </TouchableOpacity>
      ),
    });
  }, [navigation, filters, categoryOptions, sourceOptions]);

  const loadMore = () => {
    if (!nextUrl || loadingMore) return;
    setLoadingMore(true);
    apiClient
      .get(nextUrl)
      .then((res) => {
        const moreResults = res.data.results ?? [];
        setRawOpportunities((prev) => [...prev, ...moreResults]);
        setNextUrl(res.data.next ?? null);
      })
      .catch((err) => console.log('Error loading more opportunities:', err.message))
      .finally(() => setLoadingMore(false));
  };

  const onRefresh = () => {
    fetchOpportunities(true);
  };

  const displayedOpportunities = rawOpportunities.filter((o) => {
    if (filters.category && o.primary_category !== filters.category) return false;
    if (filters.source && o.source_name !== filters.source) return false;
    if (filters.minScore > 0 && o.score < filters.minScore) return false;
    if (filters.datePreset !== 'any') {
      const days = filters.datePreset === '24h' ? 1 : filters.datePreset === '7d' ? 7 : 30;
      const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
      const published = o.source_published_at ? new Date(o.source_published_at).getTime() : 0;
      if (published < cutoff) return false;
    }
    return true;
  });

  if (loading) return <ActivityIndicator style={{ flex: 1 }} size="large" />;

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Opportunity Queue</Text>
      <FlatList
        data={displayedOpportunities}
        keyExtractor={(item) => String(item.id)}
        ListEmptyComponent={<Text style={styles.empty}>No opportunities match these filters.</Text>}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        onEndReached={loadMore}
        onEndReachedThreshold={0.5}
        ListFooterComponent={loadingMore ? <ActivityIndicator style={{ marginVertical: 16 }} /> : null}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.card} onPress={() => navigation.navigate('LeadDetail', { id: item.id })}>
            <Text style={styles.cardTitle}>{item.requirement ?? 'Untitled'}</Text>
            <View style={styles.cardMetaRow}>
              <Text style={[styles.cardBand, { color: BAND_COLORS[item.band] ?? '#4b5f5a' }]}>{item.band}</Text>
              <Text style={styles.cardScore}>Score: {item.score}</Text>
            </View>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f3ee' },
  header: { fontSize: 20, fontWeight: '700', padding: 16, color: '#10201c' },
  empty: { textAlign: 'center', marginTop: 40, color: '#6b7873' },
  card: { backgroundColor: '#fff', marginHorizontal: 16, marginBottom: 10, padding: 14, borderRadius: 10, borderWidth: 1, borderColor: '#e3e0d8' },
  cardTitle: { fontSize: 15, fontWeight: '600', color: '#10201c', marginBottom: 6 },
  cardMetaRow: { flexDirection: 'row', justifyContent: 'space-between' },
  cardBand: { fontSize: 13, fontWeight: '600' },
  cardScore: { fontSize: 13, color: '#4b5f5a' },
});