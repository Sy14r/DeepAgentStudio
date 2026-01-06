import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '../card';

describe('Card', () => {
  it('should render card with all parts', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Card Title</CardTitle>
          <CardDescription>Card Description</CardDescription>
        </CardHeader>
        <CardContent>Card Content</CardContent>
        <CardFooter>Card Footer</CardFooter>
      </Card>
    );

    expect(screen.getByText('Card Title')).toBeInTheDocument();
    expect(screen.getByText('Card Description')).toBeInTheDocument();
    expect(screen.getByText('Card Content')).toBeInTheDocument();
    expect(screen.getByText('Card Footer')).toBeInTheDocument();
  });

  it('should apply base card classes', () => {
    render(<Card data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    expect(card).toHaveClass('rounded-lg', 'border', 'bg-card', 'shadow-sm');
  });

  it('should merge custom className on Card', () => {
    render(
      <Card className="custom-card" data-testid="card">
        Content
      </Card>
    );
    expect(screen.getByTestId('card')).toHaveClass('custom-card');
  });

  it('should apply CardHeader classes', () => {
    render(
      <Card>
        <CardHeader data-testid="header">Header</CardHeader>
      </Card>
    );
    expect(screen.getByTestId('header')).toHaveClass('flex', 'flex-col', 'p-6');
  });

  it('should apply CardTitle classes', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle data-testid="title">Title</CardTitle>
        </CardHeader>
      </Card>
    );
    expect(screen.getByTestId('title')).toHaveClass('text-2xl', 'font-semibold');
  });

  it('should apply CardDescription classes', () => {
    render(
      <Card>
        <CardHeader>
          <CardDescription data-testid="description">Description</CardDescription>
        </CardHeader>
      </Card>
    );
    expect(screen.getByTestId('description')).toHaveClass('text-sm', 'text-muted-foreground');
  });

  it('should apply CardContent classes', () => {
    render(
      <Card>
        <CardContent data-testid="content">Content</CardContent>
      </Card>
    );
    expect(screen.getByTestId('content')).toHaveClass('p-6', 'pt-0');
  });

  it('should apply CardFooter classes', () => {
    render(
      <Card>
        <CardFooter data-testid="footer">Footer</CardFooter>
      </Card>
    );
    expect(screen.getByTestId('footer')).toHaveClass('flex', 'items-center', 'p-6', 'pt-0');
  });
});
