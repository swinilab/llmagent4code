/*
  Warnings:

  - You are about to drop the column `uid` on the `customers` table. All the data in the column will be lost.
  - You are about to drop the column `uid` on the `invoices` table. All the data in the column will be lost.
  - You are about to drop the column `uid` on the `orders` table. All the data in the column will be lost.
  - You are about to drop the column `uid` on the `payments` table. All the data in the column will be lost.
  - You are about to drop the column `uid` on the `products` table. All the data in the column will be lost.

*/
-- DropIndex
DROP INDEX "public"."customers_uid_key";

-- DropIndex
DROP INDEX "public"."invoices_uid_key";

-- DropIndex
DROP INDEX "public"."orders_uid_key";

-- DropIndex
DROP INDEX "public"."payments_uid_key";

-- DropIndex
DROP INDEX "public"."products_uid_key";

-- AlterTable
ALTER TABLE "public"."customers" DROP COLUMN "uid";

-- AlterTable
ALTER TABLE "public"."invoices" DROP COLUMN "uid";

-- AlterTable
ALTER TABLE "public"."orders" DROP COLUMN "uid";

-- AlterTable
ALTER TABLE "public"."payments" DROP COLUMN "uid";

-- AlterTable
ALTER TABLE "public"."products" DROP COLUMN "uid";
