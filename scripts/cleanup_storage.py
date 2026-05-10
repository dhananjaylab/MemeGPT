#!/usr/bin/env python3
"""
Standalone script for storage cleanup.

Can be run as a cron job or manually for maintenance.

Usage:
    python scripts/cleanup_storage.py --dry-run
    python scripts/cleanup_storage.py --max-age-days 7
    python scripts/cleanup_storage.py --max-size-mb 1000
    python scripts/cleanup_storage.py --migrate-to-r2
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from services.storage_cleanup import cleanup_service, run_scheduled_cleanup


async def main():
    parser = argparse.ArgumentParser(description="Storage cleanup utility")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=7,
        help="Maximum age of files in days (default: 7)"
    )
    parser.add_argument(
        "--max-size-mb",
        type=int,
        default=1000,
        help="Maximum total size in MB (default: 1000)"
    )
    parser.add_argument(
        "--cleanup-age",
        action="store_true",
        help="Clean up files older than max-age-days"
    )
    parser.add_argument(
        "--cleanup-size",
        action="store_true",
        help="Clean up oldest files until size is below max-size-mb"
    )
    parser.add_argument(
        "--migrate-to-r2",
        action="store_true",
        help="Migrate local files to R2 storage"
    )
    parser.add_argument(
        "--delete-after-migration",
        action="store_true",
        help="Delete local files after successful R2 migration"
    )
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Run the full scheduled cleanup routine"
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Show storage metrics only"
    )
    
    args = parser.parse_args()
    
    # Show metrics
    if args.metrics or not any([
        args.cleanup_age,
        args.cleanup_size,
        args.migrate_to_r2,
        args.scheduled
    ]):
        print("\n=== Storage Metrics ===")
        metrics = cleanup_service.get_storage_metrics()
        for key, value in metrics.items():
            print(f"{key}: {value}")
        print()
    
    # Run scheduled cleanup
    if args.scheduled:
        print("\n=== Running Scheduled Cleanup ===")
        result = await run_scheduled_cleanup()
        print(f"\nBefore: {result['before']}")
        print(f"Cleanup: {result['cleanup']}")
        print(f"After: {result['after']}")
        return
    
    # Cleanup by age
    if args.cleanup_age:
        print(f"\n=== Cleaning up files older than {args.max_age_days} days ===")
        result = cleanup_service.cleanup_old_files(
            max_age_days=args.max_age_days,
            dry_run=args.dry_run
        )
        print(f"Deleted: {result['deleted_count']} files")
        print(f"Freed: {result['freed_mb']} MB")
        if result['errors']:
            print(f"Errors: {len(result['errors'])}")
            for error in result['errors']:
                print(f"  - {error}")
    
    # Cleanup by size
    if args.cleanup_size:
        print(f"\n=== Cleaning up to reach {args.max_size_mb} MB ===")
        result = cleanup_service.cleanup_by_size(
            target_size_mb=args.max_size_mb,
            dry_run=args.dry_run
        )
        print(f"Deleted: {result['deleted_count']} files")
        print(f"Freed: {result['freed_mb']} MB")
        print(f"Final size: {result.get('final_size_mb', 'N/A')} MB")
        if result.get('errors'):
            print(f"Errors: {len(result['errors'])}")
            for error in result['errors']:
                print(f"  - {error}")
    
    # Migrate to R2
    if args.migrate_to_r2:
        print("\n=== Migrating to R2 Storage ===")
        result = await cleanup_service.migrate_to_r2(
            delete_after_upload=args.delete_after_migration
        )
        print(f"Total files: {result['total_files']}")
        print(f"Migrated: {result['migrated_count']}")
        print(f"Failed: {result['failed_count']}")
        print(f"Deleted: {result['deleted_count']}")
        if result['errors']:
            print(f"Errors: {len(result['errors'])}")
            for error in result['errors'][:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(result['errors']) > 10:
                print(f"  ... and {len(result['errors']) - 10} more")
    
    print()


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
