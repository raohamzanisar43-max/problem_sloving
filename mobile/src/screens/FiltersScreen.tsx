import React, { useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, TextInput } from 'react-native';

const INTENT_OPTIONS = [
  { label: 'Buyer', value: 'buyer' },
  { label: 'Hiring', value: 'hiring' },
{ label: 'Non-buyer', value: 'nonbuyer' },
  { label: 'Uncertain', value: 'uncertain' },
];

const STATUS_OPTIONS = [
  { label: 'New', value: 'new' },
  { label: 'Review', value: 'review' },
  { label: 'Contacted', value: 'contacted' },
  { label: 'Closed', value: 'closed' },
  { label: 'Rejected', value: 'rejected' },
];

const BAND_OPTIONS = [
  { label: 'Hot', value: 'Hot' },
  { label: 'High potential', value: 'High potential' },
  { label: 'Review', value: 'Review' },
  { label: 'Archive', value: 'Archive' },
];

const DATE_OPTIONS = [
  { label: 'Any time', value: 'any' },
  { label: 'Last 24 hours', value: '24h' },
  { label: 'Last 7 days', value: '7d' },
  { label: 'Last 30 days', value: '30d' },
];

export default function FiltersScreen({ navigation, route }: any) {
  const { filters: initialFilters, categoryOptions = [], sourceOptions = [] } = route.params ?? {};
  const [intent, setIntent] = useState<string | null>(initialFilters?.intent ?? null);
  const [status, setStatus] = useState<string | null>(initialFilters?.status ?? null);
  const [band, setBand] = useState<string | null>(initialFilters?.band ?? null);
  const [category, setCategory] = useState<string | null>(initialFilters?.category ?? null);
  const [source, setSource] = useState<string | null>(initialFilters?.source ?? null);
  const [minScore, setMinScore] = useState(String(initialFilters?.minScore ?? 0));
  const [datePreset, setDatePreset] = useState(initialFilters?.datePreset ?? 'any');

  const applyFilters = () => {
    navigation.navigate('OpportunityQueue', {
      filters: {
        intent,
        status,
        band,
        category,
        source,
        minScore: parseInt(minScore, 10) || 0,
        datePreset,
      },
    });
  };

  const clearFilters = () => {
    navigation.navigate('OpportunityQueue', {
      filters: { intent: null, status: null, band: null, category: null, source: null, minScore: 0, datePreset: 'any' },
    });
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <FilterSection label="Intent" options={INTENT_OPTIONS} selected={intent} onSelect={setIntent} />
        <FilterSection label="Status" options={STATUS_OPTIONS} selected={status} onSelect={setStatus} />
        <FilterSection label="Score band" options={BAND_OPTIONS} selected={band} onSelect={setBand} />
        {categoryOptions.length > 0 && (
          <FilterSection
            label="Category"
            options={categoryOptions.map((c: string) => ({ label: c, value: c }))}
            selected={category}
            onSelect={setCategory}
          />
        )}
        {sourceOptions.length > 0 && (
          <FilterSection
            label="Source"
            options={sourceOptions.map((s: string) => ({ label: s, value: s }))}
            selected={source}
            onSelect={setSource}
          />
        )}
        <Text style={styles.sectionLabel}>Minimum score</Text>
        <TextInput
          style={styles.scoreInput}
          keyboardType="number-pad"
          value={minScore}
          onChangeText={setMinScore}
          placeholder="0"
        />
        <FilterSection label="Detected within" options={DATE_OPTIONS} selected={datePreset} onSelect={setDatePreset} />
      </ScrollView>
      <View style={styles.footer}>
        <TouchableOpacity style={styles.clearButton} onPress={clearFilters}>
          <Text style={styles.clearButtonText}>Clear all</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.applyButton} onPress={applyFilters}>
          <Text style={styles.applyButtonText}>Apply filters</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

function FilterSection({ label, options, selected, onSelect }: any) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionLabel}>{label}</Text>
      <View style={styles.chipRow}>
        {options.map((opt: any) => (
          <TouchableOpacity
            key={opt.value}
            style={[styles.chip, selected === opt.value && styles.chipActive]}
            onPress={() => onSelect(selected === opt.value ? null : opt.value)}
          >
            <Text style={[styles.chipText, selected === opt.value && styles.chipTextActive]}>{opt.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f3ee' },
  scroll: { padding: 16, paddingBottom: 32 },
  section: { marginBottom: 20 },
  sectionLabel: { fontSize: 14, fontWeight: '600', color: '#10201c', marginBottom: 8 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { paddingVertical: 8, paddingHorizontal: 14, borderRadius: 20, borderWidth: 1, borderColor: '#d3ddd9', backgroundColor: '#fff' },
  chipActive: { backgroundColor: '#0f8a5f', borderColor: '#0f8a5f' },
  chipText: { fontSize: 13, color: '#4b5f5a', fontWeight: '500' },
  chipTextActive: { color: '#fff' },
  scoreInput: { borderWidth: 1, borderColor: '#d3ddd9', borderRadius: 8, padding: 10, backgroundColor: '#fff', width: 100, marginBottom: 20 },
  footer: { flexDirection: 'row', padding: 16, gap: 12, borderTopWidth: 1, borderTopColor: '#e3e0d8', backgroundColor: '#f5f3ee' },
  clearButton: { flex: 1, padding: 14, borderRadius: 8, borderWidth: 1, borderColor: '#d3ddd9', alignItems: 'center' },
  clearButtonText: { color: '#4b5f5a', fontWeight: '600' },
  applyButton: { flex: 2, padding: 14, borderRadius: 8, backgroundColor: '#0f8a5f', alignItems: 'center' },
  applyButtonText: { color: '#fff', fontWeight: '600' },
});