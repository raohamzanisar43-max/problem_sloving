import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import LoginScreen from '../screens/LoginScreen';
import DashboardScreen from '../screens/DashboardScreen';
import OpportunityQueueScreen from '../screens/OpportunityQueueScreen';
import LeadDetailScreen from '../screens/LeadDetailScreen';
import FiltersScreen from '../screens/FiltersScreen';
import ReviewScreen from '../screens/ReviewScreen';
import SalesPipelineScreen from '../screens/SalesPipelineScreen';
import SourceHealthScreen from '../screens/SourceHealthScreen';
import SettingsScreen from '../screens/SettingsScreen';

const Stack = createNativeStackNavigator();

export default function AppNavigator() {
  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        <Stack.Screen name="Login" component={LoginScreen} />
        <Stack.Screen name="Dashboard" component={DashboardScreen} options={{ headerShown: true, title: 'Dashboard' }} />
        <Stack.Screen name="OpportunityQueue" component={OpportunityQueueScreen} options={{ headerShown: true, title: 'Opportunities' }} />
        <Stack.Screen name="LeadDetail" component={LeadDetailScreen} options={{ headerShown: true, title: 'Lead Detail' }} />
        <Stack.Screen name="Filters" component={FiltersScreen} options={{ headerShown: true, title: 'Filters', presentation: 'modal' }} />
        <Stack.Screen name="Review" component={ReviewScreen} options={{ headerShown: true, title: 'Review Queue' }} />
        <Stack.Screen name="SalesPipeline" component={SalesPipelineScreen} options={{ headerShown: true, title: 'Sales Pipeline' }} />
        <Stack.Screen name="SourceHealth" component={SourceHealthScreen} options={{ headerShown: true, title: 'Source Health' }} />
        <Stack.Screen name="Settings" component={SettingsScreen} options={{ headerShown: true, title: 'Settings' }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}