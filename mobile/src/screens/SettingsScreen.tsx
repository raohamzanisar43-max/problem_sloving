import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity, Alert } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import apiClient from '../api/apiClient';

export default function SettingsScreen({ navigation }: any) {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get('/me/')
      .then((res) => setUser(res.data))
      .catch((err) => console.log('Error loading account:', err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleLogout = () => {
    Alert.alert('Logout', 'Are you sure you want to log out?', [
              { text: 'Cancel', style: 'cancel' },
      {
        text: 'Logout',
        style: 'destructive',
        onPress: async () => {
          await SecureStore.deleteItemAsync('access_token');
          await SecureStore.deleteItemAsync('refresh_token');
          navigation.reset({ index: 0, routes: [{ name: 'Login' }] });
        },
      },
    ]);
  };

  if (loading) return <ActivityIndicator style={{ flex: 1 }} size="large" />;

  return (
    <View style={styles.container}>
      <Text style={styles.sectionLabel}>Account</Text>
      <View style={styles.card}>
        <Row label="Username" value={user?.username ?? '—'} />
        <Row label="Role" value={user?.role ?? '—'} />
        <Row label="Email" value={user?.email ?? '—'} />
      </View>

      <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
        <Text style={styles.logoutText}>Logout</Text>
      </TouchableOpacity>
    </View>
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
  sectionLabel: { fontSize: 14, fontWeight: '600', color: '#10201c', marginBottom: 8 },
  card: { backgroundColor: '#fff', borderRadius: 10, borderWidth: 1, borderColor: '#e3e0d8', marginBottom: 24 },
  row: { flexDirection: 'row', justifyContent: 'space-between', padding: 14, borderBottomWidth: 1, borderBottomColor: '#e3e0d8' },
  rowLabel: { fontSize: 13, color: '#4b5f5a' },
  rowValue: { fontSize: 13, color: '#10201c', fontWeight: '600' },
  logoutButton: { backgroundColor: '#9b3b3b', borderRadius: 8, padding: 14, alignItems: 'center' },
  logoutText: { color: '#fff', fontWeight: '600' },
});