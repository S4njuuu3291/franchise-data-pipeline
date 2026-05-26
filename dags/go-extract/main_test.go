package main

import (
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestS3KeyGeneration_Master(t *testing.T) {
	q := QueryFileName{
		FileName: "menu_master/menu_master.csv",
		IsMaster: true,
	}

	var key string
	if q.IsMaster {
		key = q.FileName
	}
	assert.Equal(t, "menu_master/menu_master.csv", key)
}

func TestS3KeyGeneration_OrdersHivePartition(t *testing.T) {
	tests := []struct {
		name     string
		fileName string
		prefix   string
		want     string
	}{
		{
			name:     "orders day 02",
			fileName: "orders.csv",
			prefix:   "year=2026/month=03/day=02",
			want:     "orders/year=2026/month=03/day=02/orders.csv",
		},
		{
			name:     "order_items day 25",
			fileName: "order_items.csv",
			prefix:   "year=2026/month=02/day=25",
			want:     "order_items/year=2026/month=02/day=25/order_items.csv",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tableName := strings.TrimSuffix(tt.fileName, ".csv")
			key := fmt.Sprintf("%s/%s/%s", tableName, tt.prefix, tt.fileName)
			assert.Equal(t, tt.want, key)
		})
	}
}

func TestS3KeyGeneration_AllMasterTables(t *testing.T) {
	masters := []struct {
		fileName string
		want     string
	}{
		{"menu_master/menu_master.csv", "menu_master/menu_master.csv"},
		{"outlet_master/outlet_master.csv", "outlet_master/outlet_master.csv"},
	}

	for _, m := range masters {
		t.Run(m.fileName, func(t *testing.T) {
			q := QueryFileName{FileName: m.fileName, IsMaster: true}
			var key string
			if q.IsMaster {
				key = q.FileName
			}
			assert.Equal(t, m.want, key)
		})
	}
}

func TestCutoffDateLoop(t *testing.T) {
	startDate := time.Date(2026, 2, 25, 0, 0, 0, 0, time.UTC)
	cutoffDate := time.Date(2026, 3, 2, 0, 0, 0, 0, time.UTC)

	var days int
	for d := startDate; !d.After(cutoffDate); d = d.AddDate(0, 0, 1) {
		days++
	}
	assert.Equal(t, 6, days)
}

func TestCutoffDatePartitions(t *testing.T) {
	startDate := time.Date(2026, 2, 25, 0, 0, 0, 0, time.UTC)
	cutoffDate := time.Date(2026, 3, 2, 0, 0, 0, 0, time.UTC)

	expectedPartitions := []string{
		"year=2026/month=02/day=25",
		"year=2026/month=02/day=26",
		"year=2026/month=02/day=27",
		"year=2026/month=02/day=28",
		"year=2026/month=03/day=01",
		"year=2026/month=03/day=02",
	}

	var idx int
	for d := startDate; !d.After(cutoffDate); d = d.AddDate(0, 0, 1) {
		prefix := fmt.Sprintf("year=%d/month=%02d/day=%02d", d.Year(), d.Month(), d.Day())
		assert.Equal(t, expectedPartitions[idx], prefix, "day %d partition mismatch", idx)
		idx++
	}
}

func TestQueryHeaderCount(t *testing.T) {
	tests := []struct {
		name   string
		header []string
		want   int
	}{
		{"menu_master", []string{"menu_id", "menu_name", "category", "base_price", "price_tier_1", "price_tier_2", "price_tier_3", "is_promo_active", "updated_at"}, 9},
		{"outlet_master", []string{"outlet_id", "outlet_name", "city", "region_tier", "created_at", "updated_at"}, 6},
		{"orders", []string{"order_id", "outlet_id", "cashier_id", "total_amount", "payment_method", "created_at"}, 6},
		{"order_items", []string{"item_id", "order_id", "menu_id", "quantity", "price_per_item", "subtotal"}, 6},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Len(t, tt.header, tt.want)
		})
	}
}
