<template>
	<div class="payment-references">
		<div class="payment-references__header">
			<p class="payment-references__label">{{ __("Transaction References") }}</p>
			<span class="payment-references__total">
				{{ __("Referenced Total") }}: {{ formatCurrency(referencedTotal) }}
			</span>
		</div>

		<div v-if="payment.references && payment.references.length" class="payment-references__rows">
			<div v-for="(row, index) in payment.references" :key="index" class="payment-references__row">
				<div class="payment-references__fields">
					<v-text-field
						:model-value="row.transaction_reference"
						:label="__('Transaction Ref')"
						density="compact"
						variant="solo"
						hide-details
						class="sleek-field pos-themed-input"
						@update:model-value="
							$emit('update-reference', index, 'transaction_reference', $event)
						"
					/>
					<v-text-field
						:model-value="formatCurrency(row.amount)"
						:label="__('Amount')"
						density="compact"
						variant="solo"
						hide-details
						class="sleek-field pos-themed-input"
						:prefix="currencySymbol ? currencySymbol(currency) : undefined"
						@change="$emit('update-reference', index, 'amount', $event.target.value)"
					/>
					<v-btn
						icon
						size="small"
						variant="text"
						color="error"
						:aria-label="__('Remove')"
						@click="$emit('remove-reference', index)"
					>
						<v-icon size="18">mdi-delete-outline</v-icon>
					</v-btn>
				</div>
				<p v-if="rowErrors[index]" class="payment-references__error">{{ rowErrors[index] }}</p>
			</div>
		</div>

		<v-btn
			variant="tonal"
			size="small"
			color="primary"
			class="payment-references__add"
			@click="$emit('add-reference')"
		>
			{{ __("Add Transaction") }}
		</v-btn>
	</div>
</template>

<script setup>
import { computed } from "vue";

const __ = window.__;

const props = defineProps({
	payment: {
		type: Object,
		required: true,
	},
	currency: String,
	currencySymbol: Function,
	remaining: {
		type: Number,
		default: 0,
	},
	formatCurrency: {
		type: Function,
		required: true,
	},
});

defineEmits(["add-reference", "update-reference", "remove-reference"]);

const referencedTotal = computed(() =>
	(props.payment.references || []).reduce((sum, row) => sum + (parseFloat(row.amount) || 0), 0),
);

const rowErrors = computed(() => {
	const references = props.payment.references || [];
	const seen = new Map();

	return references.map((row) => {
		const ref = String(row.transaction_reference || "").trim();
		const amount = parseFloat(row.amount) || 0;

		if (!ref) {
			return __("Transaction reference cannot be blank.");
		}
		if (amount <= 0) {
			return __("Amount must be greater than zero.");
		}

		const key = ref.toLowerCase();
		if (seen.has(key)) {
			return __("Duplicate transaction reference.");
		}
		seen.set(key, true);

		return "";
	});
});
</script>

<style scoped>
.payment-references {
	display: flex;
	flex-direction: column;
	gap: var(--pos-space-2);
	padding: var(--pos-space-3);
	margin-top: var(--pos-space-2);
	border-radius: var(--pos-radius-md);
	border: 1px solid var(--pos-border-light);
	background: var(--pos-surface-raised);
}

.payment-references__header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--pos-space-2);
}

.payment-references__label {
	margin: 0;
	font-size: 0.72rem;
	font-weight: 700;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--pos-text-secondary);
}

.payment-references__total {
	font-size: 0.82rem;
	font-weight: 700;
	color: var(--pos-text-primary);
}

.payment-references__rows {
	display: flex;
	flex-direction: column;
	gap: var(--pos-space-2);
}

.payment-references__row {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.payment-references__fields {
	display: flex;
	align-items: center;
	gap: var(--pos-space-2);
}

.payment-references__fields > * {
	flex: 1;
}

.payment-references__error {
	margin: 0;
	font-size: 0.76rem;
	font-weight: 600;
	color: rgb(var(--v-theme-error));
}

.payment-references__add {
	align-self: flex-start;
	text-transform: none;
	font-weight: 700;
}
</style>
