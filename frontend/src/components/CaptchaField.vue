<template>
  <div class="captcha">
    <div class="captcha-image" @click="$emit('refresh')" title="Click to refresh">
      <img v-if="image" :src="image" alt="CAPTCHA" />
      <span v-else class="placeholder">Loading...</span>
    </div>
    <input
      :value="modelValue"
      placeholder="CAPTCHA*"
      maxlength="10"
      pattern="[A-Za-z0-9]+"
      required
      autocomplete="off"
      class="captcha-input"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{ image: string; modelValue: string }>()
defineEmits<{ (e: 'update:modelValue', v: string): void; (e: 'refresh'): void }>()
</script>

<style scoped>
.captcha {
  display: flex;
  align-items: center;
  gap: 10px;
}

.captcha-image {
  cursor: pointer;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  overflow: hidden;
  background: #f9fafb;
  flex-shrink: 0;
}

.captcha-image img {
  display: block;
  height: 48px;
  width: auto;
}

.placeholder {
  display: block;
  width: 120px;
  height: 48px;
  line-height: 48px;
  text-align: center;
  font-size: 12px;
  color: #9ca3af;
}

.captcha-input {
  flex: 1;
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.captcha-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}
</style>
