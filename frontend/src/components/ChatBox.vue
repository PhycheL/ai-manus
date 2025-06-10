<template>
    <div class="pb-3 relative bg-[var(--background-gray-main)]">
        <div
            class="flex flex-col gap-3 rounded-[22px] transition-all relative bg-[var(--fill-input-chat)] py-3 max-h-[300px] shadow-[0px_12px_32px_0px_rgba(0,0,0,0.02)] border border-black/8 dark:border-[var(--border-main)]">
            <div class="overflow-y-auto pl-4 pr-2">
                <textarea
                    class="flex rounded-md border-input focus-visible:outline-none focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 overflow-hidden flex-1 bg-transparent p-0 pt-[1px] border-0 focus-visible:ring-0 focus-visible:ring-offset-0 w-full placeholder:text-[var(--text-disable)] text-[15px] shadow-none resize-none min-h-[40px]"
                    :rows="rows" :value="modelValue"
                    @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
                    @compositionstart="isComposing = true" @compositionend="isComposing = false"
                    @keydown.enter.exact="handleEnterKeydown" :placeholder="t('Give Manus a task to work on...')"
                    :style="{ height: '46px' }"></textarea>
            </div>
            <footer class="flex flex-row justify-between w-full px-3">
                <div class="flex gap-2 pr-2 items-center">
                    <button
                        @click="triggerFileUpload"
                        class="w-8 h-8 rounded-full flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                        title="上传文件"
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="text-gray-500 dark:text-gray-400">
                            <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66L9.64 16.2a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
                        </svg>
                    </button>
                    
                    <input 
                        ref="fileInput"
                        type="file" 
                        multiple 
                        accept=".txt,.csv,.json,.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif,.py,.js,.html,.css,.java,.cpp,.c,.xml,.md"
                        @change="handleFileChange"
                        class="hidden"
                    />
                    
                    <span v-if="selectedFiles.length > 0" class="text-xs text-gray-500 dark:text-gray-400">
                        {{ selectedFiles.length }} 个文件
                    </span>
                </div>
                <div class="flex gap-2">
                    <button
                        v-if="!isRunning || hasTextInput"
                        class="whitespace-nowrap text-sm font-medium focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 text-primary-foreground hover:bg-primary/90 p-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors hover:opacity-90"
                        :class="!hasTextInput ? 'cursor-not-allowed bg-[var(--fill-tsp-white-dark)]' : 'cursor-pointer bg-[var(--Button-primary-black)]'"
                        @click="handleSubmit">
                        <SendIcon :disabled="!hasTextInput" />
                    </button>
                    <button
                        v-else
                        @click="handleStop"
                        class="inline-flex items-center justify-center whitespace-nowrap text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring bg-[var(--Button-primary-black)] text-[var(--text-onblack)] gap-[4px] hover:opacity-90 rounded-full p-0 w-8 h-8">
                        <div class="w-[10px] h-[10px] bg-[var(--icon-onblack)] rounded-[2px]">
                        </div>
                    </button>
                </div>
            </footer>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import SendIcon from './icons/SendIcon.vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const hasTextInput = ref(false);
const isComposing = ref(false);
const fileInput = ref<HTMLInputElement>();
const selectedFiles = ref<File[]>([]);

const props = defineProps<{
    modelValue: string;
    rows: number;
    isRunning: boolean;
}>();

const emit = defineEmits<{
    (e: 'update:modelValue', value: string): void;
    (e: 'submit'): void;
    (e: 'stop'): void;
    (e: 'files-selected', files: File[]): void;
}>();

const handleEnterKeydown = (event: KeyboardEvent) => {
    if (isComposing.value) {
        // If in input method composition state, do nothing and allow default behavior
        return;
    }

    // Not in input method composition state and has text input, prevent default behavior and submit
    if (hasTextInput.value) {
        event.preventDefault();
        handleSubmit();
    }
};

const handleSubmit = () => {
    if (!hasTextInput.value) return;
    emit('submit');
};

const handleStop = () => {
    emit('stop');
};

const triggerFileUpload = () => {
    fileInput.value?.click();
};

const handleFileChange = (event: Event) => {
    const target = event.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
        selectedFiles.value = Array.from(target.files);
        emit('files-selected', selectedFiles.value);
    }
};

watch(() => props.modelValue, (value) => {
    hasTextInput.value = value.trim() !== '';
});
</script>