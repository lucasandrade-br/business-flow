import { ref } from "vue";

// Singleton: o toast é exibido no coordenador (DashboardReconciliacao) mas
// qualquer painel pode chamar notify() para disparar a notificação.
const toast = ref("");
let _timer = null;

export function notify(message) {
  toast.value = message;
  if (_timer) clearTimeout(_timer);
  _timer = setTimeout(() => {
    toast.value = "";
  }, 3000);
}

export function useToast() {
  return { toast, notify };
}
