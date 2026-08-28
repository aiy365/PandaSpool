import type {
  ApiEnvelope,
  ApiErrorPayload,
  DashboardPayload,
  EvidenceCreateInput,
  FilamentUpdateInput,
  FilamentCreateInput,
  FilamentDetail,
  InventoryMovement,
  InventorySetInput,
  ImageRecognitionResult,
  AiInventoryPacket,
  ProductCatalogPayload,
  ProductDetail,
  ProductEvidenceCreateInput,
  ProductPresetCreateInput,
} from "./types";

export class DashboardApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "DashboardApiError";
  }
}

export interface SessionInfo {
  authenticated: boolean;
  mode: "local" | "password";
  username: string | null;
}

export interface CredentialSettingsInput {
  username: string;
  current_password: string;
  new_password?: string;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    credentials: "same-origin",
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ApiErrorPayload;
    throw new DashboardApiError(
      payload.error?.message || `请求失败（${response.status}）`,
      response.status,
      payload.request_id,
    );
  }

  const payload = (await response.json()) as ApiEnvelope<T>;
  return payload.data;
}

export const dashboardApi = {
  session: () => request<SessionInfo>("/api/session"),
  login: (username: string, password: string) =>
    request<{ username: string; mode: "password" }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request("/api/auth/logout", { method: "POST", body: "{}" }),
  updateCredentials: (input: CredentialSettingsInput) =>
    request<{ username: string; reauthenticate: boolean }>("/api/auth/settings", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  list: () => request<DashboardPayload>("/api/filaments"),
  products: () => request<ProductCatalogPayload>("/api/products"),
  productDetail: (productId: string) => request<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`),
  addProductPreset: (input: ProductPresetCreateInput) =>
    request<{ preset_evaluation_id: string; source_id: string; created: boolean }>(
      "/api/products/presets",
      { method: "POST", body: JSON.stringify(input) },
    ),
  addProductEvidence: (input: ProductEvidenceCreateInput) =>
    request<{ source_id: string; inserted_claims: 0; deduplicated_source: boolean; processing_status: "pending_manual_review"; file_url: string }>(
      "/api/products/evidence",
      { method: "POST", body: JSON.stringify(input) },
    ),
  detail: (filamentId: string) => request<FilamentDetail>(`/api/filaments/${encodeURIComponent(filamentId)}`),
  createFilament: (input: FilamentCreateInput) =>
    request("/api/filaments/create", { method: "POST", body: JSON.stringify(input) }),
  movements: (filamentId?: string) =>
    request<InventoryMovement[]>(`/api/inventory/movements?limit=100${filamentId ? `&filament_id=${encodeURIComponent(filamentId)}` : ""}`),
  move: (filamentId: string, delta: number, movementType: "purchase" | "usage" | "correction", note?: string) =>
    request("/api/inventory/movement", {
      method: "POST",
      body: JSON.stringify({ filament_id: filamentId, delta, movement_type: movementType, note: note || null }),
    }),
  undo: (movementId: string) =>
    request("/api/inventory/undo", { method: "POST", body: JSON.stringify({ movement_id: movementId }) }),
  adjust: (filamentId: string, delta: number) =>
    request("/api/inventory/adjust", {
      method: "POST",
      body: JSON.stringify({ filament_id: filamentId, delta }),
    }),
  set: (input: InventorySetInput) =>
    request("/api/inventory/set-details", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  updateFilament: (input: FilamentUpdateInput) =>
    request("/api/filaments/update", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  addEvidence: (input: EvidenceCreateInput) =>
    request<{ source_id: string; inserted_claims: number; deduplicated_source: boolean; file_url: string }>(
      "/api/filaments/evidence",
      { method: "POST", body: JSON.stringify(input) },
    ),
  recognizeImage: (input: { file: { filename: string; media_type: string; data_base64: string } }) =>
    request<ImageRecognitionResult>("/api/evidence/recognize", { method: "POST", body: JSON.stringify(input) }),
  aiInventory: () => request<AiInventoryPacket>("/api/ai/inventory"),
  shutdown: () => request("/api/shutdown", { method: "POST", body: "{}" }),
};

export function userMessage(error: unknown): string {
  if (error instanceof DashboardApiError) {
    if (error.status === 401) return error.message || "登录会话已失效，请重新登录。";
    if (error.status === 429) return "登录失败次数过多，请稍后再试。";
    if (error.status === 502) return "无法读取本地耗材库，请检查磁盘空间和数据目录权限。";
    return error.message;
  }
  if (error instanceof TypeError) return "无法连接本地看板，请确认启动窗口仍在运行。";
  return "操作没有完成，请稍后重试。";
}
