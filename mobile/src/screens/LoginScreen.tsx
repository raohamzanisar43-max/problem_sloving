import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import apiClient from '../api/apiClient';

export default function LoginScreen({ navigation }: any) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setLoading(true);
    try {
      const response = await apiClient.post('/auth/token/', { username, password });
      const { access, refresh } = response.data;
      await SecureStore.setItemAsync('access_token', access);
      await SecureStore.setItemAsync('refresh_token', refresh);
      navigation.replace('Dashboard');
        } catch (error) {
      Alert.alert('Login Failed', 'Incorrect username or password, or unable to connect to the backend.');
        } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Novu Opportunity Radar</Text>
      <TextInput style={styles.input} placeholder="Username" value={username} onChangeText={setUsername} autoCapitalize="none" />
      <TextInput style={styles.input} placeholder="Password" value={password} onChangeText={setPassword} secureTextEntry />
      <TouchableOpacity style={styles.button} onPress={handleLogin} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Login</Text>}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 24, backgroundColor: '#f5f3ee' },
  title: { fontSize: 22, fontWeight: '700', marginBottom: 24, textAlign: 'center', color: '#10201c' },
  input: { borderWidth: 1, borderColor: '#d3ddd9', borderRadius: 8, padding: 12, marginBottom: 14, backgroundColor: '#fff' },
  button: { backgroundColor: '#0f8a5f', borderRadius: 8, padding: 14, alignItems: 'center', marginTop: 8 },
  buttonText: { color: '#fff', fontWeight: '600', fontSize: 16 },
});