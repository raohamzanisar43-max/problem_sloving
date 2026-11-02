import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, ScrollView, StyleSheet, ActivityIndicator, TouchableOpacity, RefreshControl } from 'react-native';
import apiClient from '../api/apiClient';

export default function DashboardScreen({ navigation }: any) {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [stats, setStats] = useState({ today: 0, hot: 0, review: 0, contacted: 0 });
  const [latest, setLatest] = useState<any[]>([]);

  const loadDashboard = useCallback(async () => {
    try {
      const [baseline, hot, review, contacted] = await Promise.all([
        apiClient.get('/opportunities/', { params: { ordering: '-detected_at' } }),
        apiClient.get('/opportunities/', { params: { band: 'Hot' } }),
        apiClient.get('/opportunities/', { params: { status: 'review' } }),
        apiClient.get('/opportunities/', { params: { status: 'contacted' } }),
      ]);

      const results = baseline.data.results ?? baseline.data;
      const todayStr = new Date().toDateString();
      const todayCount = results.filter(
        (o: any) => o.detected_at && new Date(o.detected_at).toDateString() === todayStr
      ).length;

      setStats({
        today: todayCount,
        hot: hot.data.count ?? 0,
        review: review.data.count ?? 0,
        contacted: contacted.data.count ?? 0,
      });
      setLatest(results.slice(0, 3));
    } catch (err: any) {
      console.log('Error loading dashboard:', err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const onRefresh = () => {
    setRefreshing(true);
    loadDashboard();
  };

  if (loading) return <ActivityIndicator style={{ flex: 1 }} size="large" />;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.scroll}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      <Text style={styles.welcome}>Welcome back</Text>

      <View style={styles.statsGrid}>
        <StatTile label="Today's Opportunities" value={stats.today} color="#0f8a5f" />
        <StatTile label="Hot Opportunities" value={stats.hot} color="#c2680a" />
        <StatTile label="Under Review" value={stats.review} color="#4b5f5a" onPress={() => navigation.navigate('Review')} />
        <StatTile label="Contacted" value={stats.contacted} color="#2a5d8f" />
      </View>

      <TouchableOpacity style={styles.viewAllButton} onPress={() => navigation.navigate('OpportunityQueue')}>
        <Text style={styles.viewAllText}>View All Opportunities →</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.pipelineButton} onPress={() => navigation.navigate('SalesPipeline')}>
        <Text style={styles.pipelineButtonText}>Sales Pipeline →</Text>
      </TouchableOpacity>

            <TouchableOpacity style={styles.pipelineButton} onPress={() => navigation.navigate('SourceHealth')}>
        <Text style={styles.pipelineButtonText}>Source Health →</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.pipelineButton} onPress={() => navigation.navigate('Settings')}>
        <Text style={styles.pipelineButtonText}>Settings →</Text>
      </TouchableOpacity>

      <Text style={styles.sectionTitle}>Latest Opportunities</Text>
      {latest.length === 0 && <Text style={styles.empty}>No opportunities yet.</Text>}
            {latest.map((item) => (
        <TouchableOpacity
          key={item.id}
          style={styles.latestCard}
          onPress={() => navigation.navigate('LeadDetail', { id: item.id })}
        >
          <Text style={styles.latestTitle}>{item.requirement ?? 'Untitled'}</Text>
          <Text style={styles.latestMeta}>{item.band} · Score {item.score}</Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

function StatTile({ label, value, color, onPress }: { label: string; value: number; color: string; onPress?: () => void }) {
  const Wrapper = onPress ? TouchableOpacity : View;
  return (
    <Wrapper style={styles.statTile} onPress={onPress}>
      <Text style={[styles.statValue, { color }]}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </Wrapper>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f3ee' },
  scroll: { padding: 16, paddingBottom: 32 },
  welcome: { fontSize: 22, fontWeight: '700', color: '#10201c', marginBottom: 16 },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 16 },
  statTile: { width: '47%', backgroundColor: '#fff', borderRadius: 10, padding: 16, borderWidth: 1, borderColor: '#e3e0d8' },
  statValue: { fontSize: 28, fontWeight: '700' },
  statLabel: { fontSize: 12, color: '#4b5f5a', marginTop: 4 },
  viewAllButton: { backgroundColor: '#0f8a5f', borderRadius: 8, padding: 14, alignItems: 'center', marginBottom: 24 },
  viewAllText: { color: '#fff', fontWeight: '600' },
  pipelineButton: { backgroundColor: '#fff', borderRadius: 8, padding: 14, alignItems: 'center', marginBottom: 24, borderWidth: 1, borderColor: '#0f8a5f' },
  pipelineButtonText: { color: '#0f8a5f', fontWeight: '600' },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#10201c', marginBottom: 10 },
  empty: { color: '#6b7873' },
  latestCard: { backgroundColor: '#fff', borderRadius: 10, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: '#e3e0d8' },
  latestTitle: { fontSize: 14, fontWeight: '600', color: '#10201c', marginBottom: 4 },
  latestMeta: { fontSize: 12, color: '#4b5f5a' },
});