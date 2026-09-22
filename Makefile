# ==============================================================================
# Talos Kubernetes Platform Infrastructure Automation Makefile
# ==============================================================================
# Provides standard developer workflows, multi-stage lifecycle commands,
# verification tooling, environment diagnostics, and quality gates.
# ==============================================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Paths
STAGE0_DIR  := terraform/environments/00-sandbox-hypervisor
STAGE1_DIR  := terraform/environments/01-talos-cluster
TALOS_DIR   := talos
GITOPS_DIR  := gitops
SCRIPTS_DIR := scripts
export KUBECONFIG ?= $(CURDIR)/kubeconfig

-include target.env

# Colors
BLUE   := \033[36m
GREEN  := \033[32m
YELLOW := \033[33m
RED    := \033[31m
RESET  := \033[0m

##@ 📖 Setup, Diagnostics & Quality Gates

.PHONY: help
help: ## Display this interactive help menu
	@echo -e "$(BLUE)==============================================================================$(RESET)"
	@echo -e "$(BLUE)     Talos Kubernetes Platform Infrastructure Automation Targets              $(RESET)"
	@echo -e "$(BLUE)==============================================================================$(RESET)"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

.PHONY: configure
configure: ## Interactive wizard to define, verify, and persist target deployment server
	@python3 $(SCRIPTS_DIR)/configure.py

TARGET_HOST ?= $(if $(TARGET_HOST),$(TARGET_HOST),$(shell [ -f target.env ] && grep '^TARGET_HOST=' target.env | cut -d'=' -f2 | tr -d '\"\''))

.PHONY: doctor
doctor: ## Audit local workstation developer tools, CLI binaries, and git hooks
	@python3 $(SCRIPTS_DIR)/doctor.py

.PHONY: preflight
preflight: ensure-route ## Validate target hypervisor server (KVM, libvirtd, storage pools, bridges)
	@python3 $(SCRIPTS_DIR)/preflight_server.py --host $(TARGET_HOST)

.PHONY: check-all
check-all: ## Execute both workstation doctor and target server preflight audits
	@$(MAKE) doctor
	@$(MAKE) preflight

.PHONY: route
route: ## Dynamically discover and configure local workstation route to cluster subnet
	@python3 $(SCRIPTS_DIR)/ensure_route.py

.PHONY: ensure-route
ensure-route:
	@python3 $(SCRIPTS_DIR)/ensure_route.py

##@ 🚀 Platform Lifecycle (One-Command Operations)

.PHONY: up
up: ## Provision, bootstrap, and deploy entire platform end-to-end (Stages 1 through 5)
	@echo -e "$(GREEN)===> [1/5] Provisioning Stage 1 Talos VMs...$(RESET)"
	@$(MAKE) stage1-apply
	@echo -e "$(GREEN)===> [2/5] Bootstrapping Stage 2 Talos OS & Kubernetes Control Plane...$(RESET)"
	@$(MAKE) talos-gen-config
	@$(MAKE) talos-apply-config
	@$(MAKE) talos-bootstrap
	@$(MAKE) talos-kubeconfig
	@echo -e "$(GREEN)===> [3/5] Deploying Stage 3 Networking (Cilium) & Storage (Longhorn)...$(RESET)"
	@$(MAKE) cilium-install
	@$(MAKE) longhorn-install
	@echo -e "$(GREEN)===> [4/5] Deploying Stage 4 Training Microservices...$(RESET)"
	@$(MAKE) workload-install
	@echo -e "$(GREEN)===> [5/5] Deploying Stage 5 Observability & Monitoring Stack...$(RESET)"
	@$(MAKE) monitoring-install
	@echo -e "\n$(GREEN)$(BOLD)🎉 Platform Provisioning Complete!$(RESET)"
	@echo -e "Access Dashboards with:"
	@echo -e "  - Grafana:     $(BLUE)make grafana$(RESET)     (http://localhost:3000)"
	@echo -e "  - Hubble UI:   $(BLUE)make hubble-ui$(RESET)   (http://localhost:12000)"
	@echo -e "  - Longhorn UI: $(BLUE)make longhorn$(RESET)    (http://localhost:8000)"
	@echo -e "  - ArgoCD:      $(BLUE)make argocd$(RESET)      (https://localhost:8080)\n"

.PHONY: down
down: ## Destroy cluster VMs and clean temporary state
	@echo -e "$(YELLOW)===> Tearing down Talos downstream cluster (Stage 1)...$(RESET)"
	@$(MAKE) stage1-destroy
	@echo -e "$(YELLOW)===> Cleaning local secrets and generated configs...$(RESET)"
	@rm -f kubeconfig talos/talosconfig talos/controlplane.yaml talos/worker.yaml
	@echo -e "$(GREEN)Cluster teardown complete.$(RESET)"

.PHONY: status
status: ensure-route ## Quick health and readiness overview of nodes, storage, and services
	@echo -e "$(BLUE)==============================================================================$(RESET)"
	@echo -e "$(BLUE)     Talos Kubernetes Platform Live Status                                    $(RESET)"
	@echo -e "$(BLUE)==============================================================================$(RESET)"
	@echo -e "\n$(BOLD)Kubernetes Nodes:$(RESET)"
	@kubectl get nodes -o wide 2>/dev/null || echo "Cluster offline or unreachable"
	@echo -e "\n$(BOLD)Training Workload Pods:$(RESET)"
	@kubectl get pods -n training 2>/dev/null || true
	@echo -e "\n$(BOLD)Non-Running / Pending Pods (if any):$(RESET)"
	@kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded 2>/dev/null || echo "All pods running."
	@echo -e "\n$(BOLD)Storage Classes & Persistent Volumes:$(RESET)"
	@kubectl get sc,pvc -A 2>/dev/null || true

.PHONY: test-all
test-all: ## Execute full platform test suite across all milestones (M1-M6)
	@echo -e "$(GREEN)===> Running All Milestone Test Suites (M1 through M6)...$(RESET)"
	@$(MAKE) test-m1
	@$(MAKE) test-m2
	@$(MAKE) test-m3
	@$(MAKE) test-m4
	@$(MAKE) test-m5
	@$(MAKE) test-m6
	@echo -e "\n$(GREEN)$(BOLD)🎉 All Milestone Test Suites Passed!$(RESET)\n"

##@ 🏗️ Stage 0: Nested Sandbox Hypervisor (00-sandbox-hypervisor)

.PHONY: stage0-init
stage0-init: ## Initialize Terraform providers for Stage 0
	@echo -e "$(GREEN)===> Initializing Stage 0 Nested Sandbox workspace...$(RESET)"
	terraform -chdir=$(STAGE0_DIR) init

.PHONY: stage0-plan
stage0-plan: ## Generate and review execution plan for Stage 0
	@echo -e "$(GREEN)===> Planning Stage 0 Nested Sandbox infrastructure...$(RESET)"
	terraform -chdir=$(STAGE0_DIR) plan

.PHONY: stage0-apply
stage0-apply: ## Provision Stage 0 Nested Sandbox VM hypervisor & auto-sync target
	@echo -e "$(GREEN)===> Applying Stage 0 Nested Sandbox infrastructure...$(RESET)"
	terraform -chdir=$(STAGE0_DIR) apply
	@python3 $(SCRIPTS_DIR)/sync_target.py

.PHONY: sync-target
sync-target: ## Synchronize Stage 0 Sandbox VM target details into target.env and Stage 1 tfvars
	@python3 $(SCRIPTS_DIR)/sync_target.py

.PHONY: verify-stage0
verify-stage0: ## Run automated verification checks on Stage 0 sandbox hypervisor
	@echo -e "$(GREEN)===> Running Stage 0 verification test suite...$(RESET)"
	@python3 $(SCRIPTS_DIR)/verify_stage0.py

.PHONY: stage0-destroy
stage0-destroy: ## Destroy Stage 0 Nested Sandbox infrastructure
	@echo -e "$(YELLOW)===> Destroying Stage 0 Nested Sandbox infrastructure...$(RESET)"
	terraform -chdir=$(STAGE0_DIR) destroy

##@ 🚀 Stage 1: Talos Downstream Cluster VMs (01-talos-cluster)

.PHONY: stage1-init
stage1-init: ## Initialize Terraform providers for Stage 1
	@echo -e "$(GREEN)===> Initializing Stage 1 Talos Cluster workspace...$(RESET)"
	terraform -chdir=$(STAGE1_DIR) init

.PHONY: stage1-plan
stage1-plan: ## Generate and review execution plan for Stage 1
	@echo -e "$(GREEN)===> Planning Stage 1 Talos Cluster infrastructure...$(RESET)"
	terraform -chdir=$(STAGE1_DIR) plan

.PHONY: stage1-apply
stage1-apply: ## Provision Stage 1 Talos Control Plane & Worker VMs
	@echo -e "$(GREEN)===> Applying Stage 1 Talos Cluster infrastructure...$(RESET)"
	terraform -chdir=$(STAGE1_DIR) apply

.PHONY: verify-stage1
verify-stage1: ## Run automated verification checks on Stage 1 Talos VMs
	@echo -e "$(GREEN)===> Running Stage 1 verification test suite...$(RESET)"
	@python3 $(SCRIPTS_DIR)/verify_stage1.py

.PHONY: stage1-destroy
stage1-destroy: ## Destroy Stage 1 Talos Cluster infrastructure
	@echo -e "$(YELLOW)===> Destroying Stage 1 Talos Cluster infrastructure...$(RESET)"
	terraform -chdir=$(STAGE1_DIR) destroy

.PHONY: test-m1
test-m1: ## Execute full Milestone 1 validation and verification test suite
	@echo -e "$(GREEN)===> Running Milestone 1 Test Suite...$(RESET)"
	@$(MAKE) fmt
	@$(MAKE) verify-stage0
	@$(MAKE) verify-stage1

##@ ⚙️ Stage 2: Talos OS & Kubernetes Bootstrapping

.PHONY: talos-gen-config
talos-gen-config: ## Generate declarative Talos machine configurations with patches
	@echo -e "$(GREEN)===> Generating Talos machine configurations...$(RESET)"
	@bash $(SCRIPTS_DIR)/generate_talos_config.sh

.PHONY: talos-apply-config
talos-apply-config: ensure-route ## Apply declarative machine configs to Control Plane & Worker nodes
	@echo -e "$(GREEN)===> Applying Talos machine configurations...$(RESET)"
	@python3 $(SCRIPTS_DIR)/bootstrap_cluster.py --apply-only

.PHONY: talos-bootstrap
talos-bootstrap: ensure-route ## Bootstrap etcd quorum and initialize upstream control plane
	@echo -e "$(GREEN)===> Bootstrapping Talos Kubernetes control plane...$(RESET)"
	@python3 $(SCRIPTS_DIR)/bootstrap_cluster.py --bootstrap-only

.PHONY: talos-kubeconfig
talos-kubeconfig: ensure-route ## Extract admin kubeconfig from Talos control plane
	@echo -e "$(GREEN)===> Extracting admin kubeconfig...$(RESET)"
	@python3 $(SCRIPTS_DIR)/bootstrap_cluster.py --kubeconfig-only

.PHONY: talos-health
talos-health: ensure-route ## Verify health of etcd, control plane components, and nodes
	@echo -e "$(GREEN)===> Auditing Talos cluster health...$(RESET)"
	@python3 $(SCRIPTS_DIR)/bootstrap_cluster.py --health-only

.PHONY: verify-stage2
verify-stage2: ensure-route ## Run automated verification checks on Stage 2 Talos bootstrapping
	@echo -e "$(GREEN)===> Running Stage 2 verification test suite...$(RESET)"
	@python3 $(SCRIPTS_DIR)/verify_stage2.py

.PHONY: test-m2
test-m2: ## Execute full Milestone 2 validation and verification test suite
	@echo -e "$(GREEN)===> Running Milestone 2 Test Suite...$(RESET)"
	@$(MAKE) talos-gen-config
	@$(MAKE) verify-stage2

##@ 🌐 Stage 3: Platform Services (Cilium CNI & Longhorn CSI)

.PHONY: cilium-install
cilium-install: ensure-route ## Deploy Cilium CNI with eBPF kube-proxy replacement and L2 policies
	@echo -e "$(GREEN)===> Deploying Cilium CNI via Helm...$(RESET)"
	helm repo add cilium https://helm.cilium.io/ 2>/dev/null || true
	helm repo update cilium
	helm upgrade --install cilium cilium/cilium --version 1.16.1 \
		--namespace kube-system \
		-f $(GITOPS_DIR)/platform/cilium/values.yaml
	@echo -e "$(GREEN)===> Applying Cilium L2 Announcement Policy & IP Pool...$(RESET)"
	kubectl apply -f $(GITOPS_DIR)/platform/cilium/l2-policy.yaml

.PHONY: cilium-verify
cilium-verify: ensure-route ## Run automated connectivity & eBPF flow tests
	@echo -e "$(GREEN)===> Running Cilium connectivity validation suite...$(RESET)"
	cilium connectivity test

.PHONY: longhorn-install
longhorn-install: ensure-route ## Deploy Longhorn distributed block storage
	@echo -e "$(GREEN)===> Deploying Longhorn CSI storage engine...$(RESET)"
	kubectl create namespace longhorn-system --dry-run=client -o yaml | kubectl apply -f -
	kubectl label namespace longhorn-system pod-security.kubernetes.io/enforce=privileged pod-security.kubernetes.io/audit=privileged pod-security.kubernetes.io/warn=privileged --overwrite
	helm repo add longhorn https://charts.longhorn.io 2>/dev/null || true
	helm repo update longhorn
	helm upgrade --install longhorn longhorn/longhorn --version 1.7.1 \
		--namespace longhorn-system \
		-f $(GITOPS_DIR)/platform/longhorn/values.yaml

.PHONY: verify-stage3
verify-stage3: ensure-route ## Run automated verification checks on Stage 3 Cilium and Longhorn
	@echo -e "$(GREEN)===> Running Stage 3 verification test suite...$(RESET)"
	@python3 $(SCRIPTS_DIR)/verify_stage3.py

.PHONY: test-m3
test-m3: ## Execute full Milestone 3 validation and verification test suite
	@echo -e "$(GREEN)===> Running Milestone 3 Test Suite...$(RESET)"
	@$(MAKE) verify-stage3

##@ 🔄 Stage 4: GitOps Delivery (ArgoCD & Workloads)

.PHONY: argocd-install
argocd-install: ## Deploy ArgoCD GitOps controller via Helm
	@echo -e "$(GREEN)===> Deploying ArgoCD via Helm...$(RESET)"
	helm repo add argo https://argoproj.github.io/argo-helm 2>/dev/null || true
	helm repo update argo
	helm upgrade --install argocd argo/argo-cd --version 7.6.8 \
		--namespace argocd --create-namespace \
		-f $(GITOPS_DIR)/platform/argocd/values.yaml

.PHONY: external-secrets-install
external-secrets-install: ## Deploy External Secrets Operator via Helm
	@echo -e "$(GREEN)===> Deploying External Secrets Operator...$(RESET)"
	helm repo add external-secrets https://charts.external-secrets.io 2>/dev/null || true
	helm repo update external-secrets
	helm upgrade --install external-secrets external-secrets/external-secrets --version 0.10.4 \
		--namespace external-secrets --create-namespace \
		-f $(GITOPS_DIR)/platform/external-secrets/values.yaml

.PHONY: gitops-bootstrap
gitops-bootstrap: ## Apply ArgoCD Root Application (App-of-Apps)
	@echo -e "$(GREEN)===> Bootstrapping ArgoCD Root App-of-Apps...$(RESET)"
	kubectl apply -f $(GITOPS_DIR)/bootstrap/root-application.yaml

.PHONY: workload-install
workload-install: ensure-route ## Deploy multi-tier communicating training application
	@echo -e "$(GREEN)===> Deploying training workload microservices...$(RESET)"
	kubectl apply -k $(GITOPS_DIR)/apps/training-app

.PHONY: workload-destroy
workload-destroy: ensure-route ## Delete training workload microservices
	@echo -e "$(YELLOW)===> Deleting training workload microservices...$(RESET)"
	kubectl delete -k $(GITOPS_DIR)/apps/training-app --ignore-not-found

.PHONY: verify-stage4
verify-stage4: ## Run automated verification checks on Stage 4 GitOps and Workloads
	@echo -e "$(GREEN)===> Running Stage 4 verification test suite...$(RESET)"
	@python3 $(SCRIPTS_DIR)/verify_stage4.py

.PHONY: test-m4
test-m4: ## Execute full Milestone 4 validation and verification test suite
	@echo -e "$(GREEN)===> Running Milestone 4 Test Suite...$(RESET)"
	@$(MAKE) verify-stage4

##@ 📊 Stage 5: Observability & Monitoring (Prometheus, Grafana & Hubble)

.PHONY: monitoring-install
monitoring-install: ensure-route ## Deploy kube-prometheus-stack, Alert Rules & Grafana Dashboards
	@echo -e "$(GREEN)===> Deploying kube-prometheus-stack...$(RESET)"
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
	helm repo update prometheus-community
	helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
		--namespace monitoring --create-namespace \
		-f $(GITOPS_DIR)/platform/monitoring/kube-prometheus-stack.yaml
	@echo -e "$(GREEN)===> Applying lab alert rules & Grafana Dashboards...$(RESET)"
	kubectl apply -f $(GITOPS_DIR)/platform/monitoring/alert-rules.yaml --namespace monitoring
	kubectl apply -f $(GITOPS_DIR)/platform/monitoring/dashboards/ --namespace monitoring

.PHONY: hubble-ui
hubble-ui: ensure-route ## Port-forward Cilium Hubble UI to http://localhost:12000
	@echo -e "$(GREEN)===> Port-forwarding Hubble UI to http://localhost:12000...$(RESET)"
	kubectl port-forward -n kube-system svc/hubble-ui 12000:80

.PHONY: grafana
grafana: ensure-route ## Port-forward Grafana dashboard to http://localhost:3000 (admin / prom-operator)
	@echo -e "$(GREEN)===> Port-forwarding Grafana to http://localhost:3000...$(RESET)"
	kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80

.PHONY: argocd
argocd: ensure-route ## Port-forward ArgoCD UI to https://localhost:8080
	@echo -e "$(GREEN)===> Port-forwarding ArgoCD UI to https://localhost:8080...$(RESET)"
	kubectl port-forward -n argocd svc/argocd-server 8080:443

.PHONY: longhorn
longhorn: ensure-route ## Port-forward Longhorn storage UI to http://localhost:8000
	@echo -e "$(GREEN)===> Port-forwarding Longhorn UI to http://localhost:8000...$(RESET)"
	kubectl port-forward -n longhorn-system svc/longhorn-frontend 8000:80

.PHONY: verify-stage5
verify-stage5: ensure-route ## Run automated verification checks on Stage 5 Observability Stack
	@echo -e "$(GREEN)===> Running Stage 5 verification test suite...$(RESET)"
	@python3 $(SCRIPTS_DIR)/verify_stage5.py

.PHONY: test-m6
test-m6: ## Execute full Milestone 6 validation and verification test suite
	@echo -e "$(GREEN)===> Running Milestone 6 Test Suite...$(RESET)"
	@$(MAKE) verify-stage5

##@ 🧪 Training Workload & Troubleshooting Drills

SCENARIO ?=

.PHONY: drill-list
drill-list: ## Display catalog of all available troubleshooting drills
	@python3 $(SCRIPTS_DIR)/drill_manager.py --list

.PHONY: drill-inject
drill-inject: ensure-route ## Inject a specific failure scenario (usage: make drill-inject SCENARIO=<id>)
	@python3 $(SCRIPTS_DIR)/drill_manager.py --inject $(SCENARIO)

.PHONY: drill-verify
drill-verify: ensure-route ## Verify symptoms of an active scenario (usage: make drill-verify SCENARIO=<id>)
	@python3 $(SCRIPTS_DIR)/drill_manager.py --verify $(SCENARIO)

.PHONY: drill-heal
drill-heal: ensure-route ## Restore healthy state (usage: make drill-heal SCENARIO=<id> or SCENARIO=all)
	@python3 $(SCRIPTS_DIR)/drill_manager.py --heal $(if $(SCENARIO),$(SCENARIO),all)

.PHONY: verify-drills
verify-drills: ## Run automated verification checks on troubleshooting drills and runbooks
	@echo -e "$(GREEN)===> Running Milestone 5 drill verification suite...$(RESET)"
	@python3 $(SCRIPTS_DIR)/verify_drills.py

.PHONY: test-m5
test-m5: ## Execute full Milestone 5 validation and verification test suite
	@echo -e "$(GREEN)===> Running Milestone 5 Test Suite...$(RESET)"
	@$(MAKE) verify-drills

##@ 🧹 Code Quality, Linting & Pre-commit

.PHONY: lint
lint: ## Run all pre-commit quality gates and linter checks
	@echo -e "$(GREEN)===> Running pre-commit validation suite...$(RESET)"
	pre-commit run --all-files

.PHONY: fmt
fmt: ## Automatically format Terraform files
	@echo -e "$(GREEN)===> Formatting Terraform manifests...$(RESET)"
	terraform fmt -recursive

.PHONY: clean
clean: ## Clean up temporary files, caches, and test artifacts
	@echo -e "$(YELLOW)===> Cleaning temporary and build artifacts...$(RESET)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".terraform.tfstate.lock.info" -delete 2>/dev/null || true
	@echo -e "$(GREEN)Clean complete.$(RESET)"
